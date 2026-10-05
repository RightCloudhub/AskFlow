"""P6 (M7): refund.submit is a declared-irreversible write; unknowns reconcile, never replay."""

import asyncio
from datetime import UTC, datetime, timedelta

import pytest

from app.services.agent.domains.refund import (
    REFUND_COMPENSATION,
    REFUND_GOAL,
    REFUND_OPERATION,
    REFUND_PERMISSION,
    REFUND_STATUS_OPERATION,
    refund_agent,
    refund_operations,
)
from app.services.agent.service.contracts import Environment, Evidence, OperationCall
from app.services.agent.service.driver import advance
from app.services.agent.service.executor import Executor
from app.services.agent.service.registry import OperationRegistry
from tests.unit.test_service_agent import SCOPE, store, task

__all__ = ["store"]

ORDER_ID = "owned"
AMOUNT_CENTS = 19900
REASON = "商品破损"
SLOW_SUBMIT_SECONDS = 0.05
FAST_TIMEOUT_SECONDS = 0.01
EVIDENCE_TTL_MINUTES = 1
EXPECTED_CALLS = 2
REFUND_ARGS = {"order_id": ORDER_ID, "amount_cents": AMOUNT_CENTS, "reason": REASON}


def refund_env(*, owner=None):
    return Environment(
        scope=SCOPE,
        permissions=frozenset({REFUND_PERMISSION, "refunds.read"}),
        available_operations=frozenset({REFUND_OPERATION, REFUND_STATUS_OPERATION}),
        facts={"order_owners": {ORDER_ID: owner or SCOPE.customer_id}},
    )


def refund_task():
    original = task()
    original.goal = REFUND_GOAL
    original.completion_condition = REFUND_GOAL
    original.inputs = dict(REFUND_ARGS)
    return original


async def ok_submit(_request):
    return {"status": "ok", "refund_id": "rf-1"}


async def refunded_status(_request):
    return {"status": "ok", "order_id": ORDER_ID, "refund_status": "refunded"}


def test_refund_contract_declares_irreversible_write():
    ops = {
        op.operation_id: op
        for op in refund_operations(submit=ok_submit, status_query=refunded_status)
    }
    submit = ops[REFUND_OPERATION]
    assert submit.effect == "write"
    assert submit.permission == REFUND_PERMISSION
    assert submit.compensation == REFUND_COMPENSATION
    assert ops[REFUND_STATUS_OPERATION].effect == "read"


@pytest.mark.asyncio
async def test_unknown_submit_is_not_replayed(store):
    calls = []

    async def slow_submit(request):
        calls.append(request)
        await asyncio.sleep(SLOW_SUBMIT_SECONDS)
        return {"status": "ok", "refund_id": "rf-1"}

    ops = refund_operations(
        submit=slow_submit,
        status_query=refunded_status,
        submit_timeout_seconds=FAST_TIMEOUT_SECONDS,
    )
    executor = Executor(OperationRegistry(ops), store)
    original = refund_task()
    await store.create(original)
    request = OperationCall(operation_id=REFUND_OPERATION, key="rf-1", arguments=dict(REFUND_ARGS))
    receipt = await executor.execute(original, request, env=refund_env())
    assert receipt.status == "unknown"
    restored = await store.load(original.task_id, SCOPE)
    duplicate = await executor.execute(restored, request, env=refund_env())
    assert duplicate.status == "unknown"
    assert len(calls) == 1
    changed = OperationCall(operation_id=REFUND_OPERATION, key="rf-2", arguments=dict(REFUND_ARGS))
    with pytest.raises(ValueError, match="reconcile_required"):
        await executor.execute(restored, changed, env=refund_env())


@pytest.mark.asyncio
async def test_refund_requires_order_ownership(store):
    invoked = []

    async def submit(request):
        invoked.append(request)
        return {"status": "ok", "refund_id": "rf-1"}

    async def observe(_task):
        return refund_env(owner="someone-else")

    agent = refund_agent(store, observe, submit=submit, status_query=refunded_status)
    original = refund_task()
    await store.create(original)
    result = await advance(agent, original.task_id, scope=SCOPE)
    assert invoked == []
    assert result.decisions[0].rejected[REFUND_OPERATION] == "precondition_failed"


@pytest.mark.asyncio
async def test_refunded_status_receipt_resolves(store):
    async def observe(_task):
        return refund_env()

    agent = refund_agent(store, observe, submit=ok_submit, status_query=refunded_status)
    original = refund_task()
    await store.create(original)
    result = await advance(agent, original.task_id, scope=SCOPE)
    assert result.status == "resolved"
    assert result.calls_used == EXPECTED_CALLS


@pytest.mark.asyncio
async def test_customer_confirmation_completes_the_wait(store):
    original = refund_task()
    observed_at = datetime.now(UTC)
    original.evidence = [
        Evidence(
            operation_id=REFUND_STATUS_OPERATION,
            source="customer_confirmed",
            data={"order_id": ORDER_ID, "refund_status": "received"},
            observed_at=observed_at,
            expires_at=observed_at + timedelta(minutes=EVIDENCE_TTL_MINUTES),
        )
    ]

    async def observe(_task):
        return refund_env()

    agent = refund_agent(store, observe, submit=ok_submit, status_query=refunded_status)
    await store.create(original)
    result = await advance(agent, original.task_id, scope=SCOPE)
    assert result.status == "resolved"
    assert result.calls_used == 0
