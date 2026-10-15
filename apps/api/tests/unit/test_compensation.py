"""Declared compensations auto-run only for plain op ids and mark the original (arch §4.6)."""

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import BaseModel

from app.services.agent.gateway.capabilities import automatic_compensation
from app.services.agent.gateway.gateway import ActionGateway
from app.services.agent.gateway.idempotency import derive_key
from app.services.agent.gateway.ledger import STATUS_COMPENSATED, LedgerAppend, LedgerStore
from app.services.agent.service.contracts import (
    Candidate,
    Environment,
    Evidence,
    Operation,
    OperationCall,
    Receipt,
    Task,
)
from app.services.agent.service.registry import OperationRegistry
from app.services.agent.service.runtime import AgentPolicy, ServiceAgent
from tests.unit.test_service_agent import SCOPE, store

__all__ = ["store"]

LOCK_PERMISSION = "locks"
ORIGINAL_KEY = "hold-1"
ACQUIRE_ARGS = {"lock_id": "L1"}
LOCK_OPERATIONS = ("lock.acquire", "lock.release")


class LockInput(BaseModel):
    lock_id: str


def _handler(calls, *, status="succeeded"):
    async def handler(request):
        calls.append(request.operation_id)
        if status != "succeeded":
            return Receipt(status=status, error_kind="permanent", error="lock_failure")
        return Receipt(
            status="succeeded",
            evidence=Evidence(
                operation_id=request.operation_id,
                source="lock-service",
                data=dict(request.arguments),
                expires_at=datetime.now(UTC) + timedelta(minutes=1),
            ),
        )

    return handler


def _operation(name, calls, *, compensation=None, status="succeeded"):
    return Operation(
        operation_id=name,
        version="1",
        effect="write",
        permission=LOCK_PERMISSION,
        input_schema=LockInput,
        handler=_handler(calls, status=status),
        precondition=lambda _args, _env: True,
        compensation=compensation,
    )


def _agent(store, calls, *, compensation, release_status="succeeded", hook=True):
    registry = OperationRegistry(
        [
            _operation("lock.acquire", calls, compensation=compensation),
            _operation("lock.release", calls, status=release_status),
        ]
    )

    async def observe(_task):
        return Environment(
            scope=SCOPE,
            available_operations=frozenset(LOCK_OPERATIONS),
            permissions=frozenset({LOCK_PERMISSION}),
        )

    async def propose(task, _env):
        if any(e.call.key == ORIGINAL_KEY for e in task.ledger):
            return []
        return [
            Candidate(
                call=OperationCall(
                    operation_id="lock.acquire", key=ORIGINAL_KEY, arguments=dict(ACQUIRE_ARGS)
                ),
                reason="hold lock",
            )
        ]

    def verify(_task, _env):
        return False

    async def compensate(task, _env):
        held = any(e.call.key == ORIGINAL_KEY and e.status == "succeeded" for e in task.ledger)
        return ORIGINAL_KEY if held else None

    return ServiceAgent(
        store,
        registry,
        AgentPolicy(
            observe=observe,
            propose=propose,
            verify=verify,
            compensate=compensate if hook else None,
        ),
    )


async def _held_task(store, calls, **kwargs):
    agent = _agent(store, calls, **kwargs)
    task = Task(scope=SCOPE, goal="lock.hold", completion_condition="lock released", owner="support")
    await store.create(task)
    await agent.tick(task.task_id, SCOPE)
    return agent, task


def _original_key(task_id: str) -> str:
    return derive_key(
        scope_id=task_id, step=ORIGINAL_KEY, capability="lock.acquire", args=dict(ACQUIRE_ARGS)
    )


@pytest.mark.asyncio
async def test_compensation_executes_declared_operation_and_marks_ledger(store):
    calls = []
    agent, task = await _held_task(store, calls, compensation="lock.release")
    done = await agent.tick(task.task_id, SCOPE)
    assert calls == ["lock.acquire", "lock.release"]
    assert done.status == "waiting_external"
    assert done.wake_condition == "owner_review:compensated"
    entry = next(e for e in done.ledger if e.call.key == f"compensate:{ORIGINAL_KEY}")
    assert entry.status == "succeeded"
    status = await agent.executor.gateway.prior_status(_original_key(task.task_id))
    assert status == STATUS_COMPENSATED


@pytest.mark.asyncio
async def test_reserved_prefixes_are_never_automatic(store):
    calls = []
    agent, task = await _held_task(store, calls, compensation="irreversible:refund.submit")
    done = await agent.tick(task.task_id, SCOPE)
    assert calls == ["lock.acquire"]
    assert done.wake_condition == "owner_review:no_safe_compensation"


@pytest.mark.asyncio
async def test_failed_compensation_parks_without_marking_original(store):
    calls = []
    agent, task = await _held_task(
        store, calls, compensation="lock.release", release_status="failed"
    )
    done = await agent.tick(task.task_id, SCOPE)
    assert calls == ["lock.acquire", "lock.release"]
    assert done.wake_condition == "owner_review:compensation_failed"
    status = await agent.executor.gateway.prior_status(_original_key(task.task_id))
    assert status == "EXECUTED"


@pytest.mark.asyncio
async def test_absent_hook_keeps_normal_flow(store):
    calls = []
    agent, task = await _held_task(store, calls, compensation="lock.release", hook=False)
    done = await agent.tick(task.task_id, SCOPE)
    assert calls == ["lock.acquire"]
    assert done.wake_condition == "owner_review:no_feasible_action"


def test_automatic_compensation_only_accepts_plain_ids():
    plain = _operation("lock.acquire", [], compensation="lock.release")
    assert automatic_compensation(plain) == "lock.release"
    assert automatic_compensation(_operation("a", [], compensation="irreversible:x")) is None
    assert automatic_compensation(_operation("b", [], compensation="owner_review:x")) is None
    assert automatic_compensation(_operation("c", [])) is None


@pytest.mark.asyncio
async def test_record_compensated_transitions_once_from_executed_or_unknown(store):
    gateway = ActionGateway(LedgerStore(store.sessions))

    def entry(key, status):
        return LedgerAppend(
            organization_id="shop",
            customer_id="customer",
            capability="lock.acquire",
            capability_version="1",
            args_hash="hash",
            idempotency_key=key,
            policy_decision={},
            policy_version="1",
            status=status,
        )

    await gateway.ledger.append(entry("k-failed", "FAILED"))
    assert await gateway.record_compensated("k-failed") is None
    await gateway.ledger.append(entry("k-ok", "EXECUTED"))
    assert await gateway.record_compensated("k-ok") is not None
    assert await gateway.prior_status("k-ok") == STATUS_COMPENSATED
    assert await gateway.record_compensated("k-ok") is None
    assert await gateway.record_compensated("missing") is None
