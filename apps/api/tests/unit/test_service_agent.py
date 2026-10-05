"""Behavioral checks for durable micro-steps, replanning and evidence boundaries."""

import asyncio
from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.database import Base
from app.services.agent.service.contracts import (
    Candidate,
    Environment,
    Evidence,
    Operation,
    OperationCall,
    Receipt,
    Scope,
    Task,
)
from app.services.agent.service.executor import Executor
from app.services.agent.service.registry import OperationRegistry
from app.services.agent.service.runtime import AgentPolicy, ServiceAgent
from app.services.agent.service.store import TaskConflict, TaskStore

SCOPE = Scope(organization_id="shop", customer_id="customer")


class OrderInput(BaseModel):
    order_id: str


def task():
    return Task(
        scope=SCOPE, goal="Find order", completion_condition="Live order status", owner="support"
    )


def environment(*names, allowed=True):
    return Environment(
        scope=SCOPE,
        available_operations=frozenset(names),
        permissions=frozenset({"orders.read"}) if allowed else frozenset(),
    )


def operation(name, handler, *, effect="read", **kwargs):
    return Operation(
        operation_id=name,
        version="1",
        effect=effect,
        permission="orders.read",
        input_schema=OrderInput,
        handler=handler,
        precondition=lambda args, env: args.order_id == "owned",
        **kwargs,
    )


def call(name="order.read", *, key="request-1"):
    return OperationCall(operation_id=name, key=key, arguments={"order_id": "owned"})


async def success(request):
    return Receipt(
        status="succeeded",
        evidence=Evidence(
            operation_id=request.operation_id,
            source="order-api",
            data={"delivered": True},
            expires_at=datetime.now(UTC) + timedelta(minutes=1),
        ),
    )


@pytest_asyncio.fixture
async def store(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'tasks.db'}")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    yield TaskStore(async_sessionmaker(engine, expire_on_commit=False))
    await engine.dispose()


@pytest.mark.asyncio
async def test_checkpoint_survives_new_store_and_scope_isolation(store):
    original = task()
    await store.create(original)
    restored = await TaskStore(store.sessions).load(original.task_id, SCOPE)
    assert restored == original
    for scope in [
        Scope(organization_id="other", customer_id="customer"),
        Scope(organization_id="shop", customer_id="other"),
    ]:
        with pytest.raises(LookupError):
            await store.load(original.task_id, scope)


@pytest.mark.asyncio
async def test_stale_worker_cannot_issue_external_operation(store):
    original = task()
    await store.create(original)
    stale = await store.load(original.task_id, SCOPE)
    original.status = "handed_off"
    await store.save(original)
    invoked = []

    async def handler(request):
        invoked.append(request)
        return await success(request)

    executor = Executor(OperationRegistry([operation("order.read", handler)]), store)
    with pytest.raises(TaskConflict):
        await executor.execute(stale, call(), env=environment("order.read"))
    assert invoked == []


@pytest.mark.asyncio
async def test_duplicate_call_returns_receipt_without_second_side_effect(store):
    original = task()
    await store.create(original)
    executor = Executor(OperationRegistry([operation("order.read", success)]), store)
    receipt = await executor.execute(original, call(), env=environment("order.read"))
    restored = await store.load(original.task_id, SCOPE)
    duplicate = await executor.execute(restored, call(), env=environment("order.read"))
    assert duplicate == receipt
    assert restored.calls_used == 1
    changed = call()
    changed.arguments["extra"] = "different"
    with pytest.raises(ValueError, match="different input"):
        await executor.execute(restored, changed, env=environment("order.read"))


@pytest.mark.asyncio
async def test_write_timeout_is_unknown_and_cannot_be_replayed(store):
    async def timeout(_request):
        await asyncio.sleep(1)

    original = task()
    await store.create(original)
    registry = OperationRegistry(
        [
            operation("refund.submit", timeout, effect="write", timeout_seconds=0.01),
        ]
    )
    executor = Executor(registry, store)
    receipt = await executor.execute(
        original, call("refund.submit"), env=environment("refund.submit")
    )
    restored = await store.load(original.task_id, SCOPE)
    assert receipt.status == "unknown"
    assert restored.status == "waiting_external"
    assert restored.wake_condition == "reconcile:request-1"
    with pytest.raises(ValueError, match="task_not_active"):
        await executor.execute(restored, call("refund.submit"), env=environment("refund.submit"))


@pytest.mark.asyncio
@pytest.mark.parametrize("problem", ["permission", "ownership", "schema", "availability"])
async def test_preconditions_fail_before_recording_or_executing(store, problem):
    original = task()
    await store.create(original)
    request = call()
    env = environment("order.read", allowed=problem != "permission")
    if problem == "ownership":
        request.arguments["order_id"] = "not-owned"
    if problem == "schema":
        request.arguments = {}
    if problem == "availability":
        env = environment()
    executor = Executor(OperationRegistry([operation("order.read", success)]), store)
    with pytest.raises(PermissionError):
        await executor.execute(original, request, env=env)
    assert (await store.load(original.task_id, SCOPE)).ledger == []


async def agent_for(store, *, available, handler=success):
    async def observe(_task):
        return environment(*available)

    async def propose(_task, _env):
        return [
            Candidate(
                call=call(name, key=f"request-{index + 1}"),
                priority=index,
                reason="Configured priority",
            )
            for index, name in enumerate(["order.live", "order.alternate"])
        ]

    registry = OperationRegistry(
        [operation(name, handler) for name in ["order.live", "order.alternate"]]
    )
    policy = AgentPolicy(
        observe=observe,
        propose=propose,
        verify=lambda task, env: any(e.data.get("delivered") for e in task.evidence),
    )
    return ServiceAgent(store, registry, policy)


@pytest.mark.asyncio
@pytest.mark.parametrize("available", [["order.live", "order.alternate"], ["order.alternate"]])
async def test_environment_changes_selection_and_verified_result_resolves(store, available):
    original = task()
    await store.create(original)
    agent = await agent_for(store, available=available)
    result = await agent.tick(original.task_id, SCOPE)
    assert result.decisions[-1].selected == available[0]
    assert result.status == "active"
    result = await agent.tick(original.task_id, SCOPE)
    assert result.status == "resolved"
    assert result.calls_used == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("invalid", ["mock", "expired", "failed"])
async def test_invalid_evidence_cannot_resolve_goal(store, invalid):
    async def handler(request):
        receipt = await success(request)
        if invalid == "expired":
            receipt.evidence.expires_at = datetime.now(UTC) - timedelta(seconds=1)
        else:
            receipt.status = invalid
        return receipt

    original = task()
    await store.create(original)
    agent = await agent_for(store, available=["order.live"], handler=handler)
    await agent.tick(original.task_id, SCOPE)
    result = await agent.tick(original.task_id, SCOPE)
    assert result.status != "resolved"


@pytest.mark.asyncio
async def test_budget_persists_across_runs(store):
    original = task()
    original.max_calls = 1
    await store.create(original)

    async def fail(_request):
        return Receipt(status="failed", error_kind="unavailable")

    agent = await agent_for(store, available=["order.live"], handler=fail)
    await agent.tick(original.task_id, SCOPE)
    result = await agent.tick(original.task_id, SCOPE)
    assert result.calls_used == 1
    assert result.status == "waiting_external"
    assert result.wake_condition == "owner_review:task_budget_exhausted"


@pytest.mark.asyncio
async def test_cancellation_keeps_running_intent_for_reconciliation(store):
    async def interrupted(_request):
        raise asyncio.CancelledError()

    original = task()
    await store.create(original)
    agent = await agent_for(store, available=["order.live"], handler=interrupted)
    with pytest.raises(asyncio.CancelledError):
        await agent.tick(original.task_id, SCOPE)
    interrupted = await store.load(original.task_id, SCOPE)
    interrupted.ledger[-1].deadline_at = datetime.now(UTC) - timedelta(seconds=1)
    await store.save(interrupted)
    result = await agent.tick(original.task_id, SCOPE)
    assert result.calls_used == 1
    assert result.status == "waiting_external"
    assert result.wake_condition == "reconcile_running_operation"
