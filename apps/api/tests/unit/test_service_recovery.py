"""Failure-to-recovery scenarios, including restart, fallback and durable write intent."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from app.services.agent.service.contracts import Candidate, Receipt
from app.services.agent.service.executor import Executor
from app.services.agent.service.lifecycle import VerifiedWakeup, wake_task
from app.services.agent.service.registry import OperationRegistry
from app.services.agent.service.runtime import AgentPolicy, ServiceAgent
from app.services.agent.service.store import TaskConflict
from tests.unit.test_service_agent import (
    SCOPE,
    OrderInput,
    agent_for,
    call,
    environment,
    operation,
    store,
    success,
    task,
)

__all__ = ["store"]

REFUND_RECEIPT = {
    "request_key": "refund.submit",
    "status": "settled",
    "amount_minor": 1000,
    "currency": "CNY",
}


class RefundStatusInput(OrderInput):
    request_key: str


async def refund_status(request):
    assert request.arguments["request_key"] == "refund.submit"
    receipt = await success(request)
    receipt.evidence.data = dict(REFUND_RECEIPT)
    return receipt


async def refund_candidates(_task, _env):
    status_call = call("refund.status", key="refund.status")
    status_call.arguments["request_key"] = "refund.submit"
    return [
        Candidate(
            call=call("refund.submit", key="refund.submit"),
            priority=0,
            reason="Submit authorized refund",
        ),
        Candidate(call=status_call, priority=1, reason="Reconcile original request"),
    ]


async def retry_due(store, task_id):
    saved = await store.load(task_id, SCOPE)
    saved.review_at = datetime.now(UTC) - timedelta(seconds=1)
    await store.save(saved)
    return VerifiedWakeup(task_id=task_id, scope=SCOPE, condition=saved.wake_condition)


@pytest.mark.asyncio
async def test_transient_read_waits_then_recovers_after_restart(store):
    calls = []

    async def flaky(request):
        calls.append(request.key)
        if len(calls) == 1:
            raise ConnectionError("private transport details")
        return await success(request)

    original = task()
    await store.create(original)
    agent = await agent_for(store, available=["order.live"], handler=flaky)
    failed = await agent.tick(original.task_id, SCOPE)
    assert failed.status == "waiting_external"
    assert failed.recovery_signals[-1].action == "retry"
    event = VerifiedWakeup(task_id=original.task_id, scope=SCOPE, condition=failed.wake_condition)
    assert not await wake_task(store, event)  # Backoff cannot be skipped by duplicate events.
    event = await retry_due(store, original.task_id)
    assert await wake_task(store, event)
    assert not await wake_task(store, event)
    restarted = await agent_for(store, available=["order.live"], handler=flaky)
    await restarted.tick(original.task_id, SCOPE)
    result = await restarted.tick(original.task_id, SCOPE)
    assert result.status == "resolved"
    assert result.calls_used == 2
    assert calls == ["request-1", "request-1:retry"]


@pytest.mark.asyncio
async def test_unavailable_operation_changes_next_plan(store):
    async def unavailable(request):
        if request.operation_id == "order.live":
            return Receipt(status="failed", error_kind="unavailable")
        return await success(request)

    original = task()
    await store.create(original)
    agent = await agent_for(store, available=["order.live", "order.alternate"], handler=unavailable)
    result = await agent.tick(original.task_id, SCOPE)
    assert result.recovery_signals[-1].action == "fallback"
    result = await agent.tick(original.task_id, SCOPE)
    assert result.decisions[-1].selected == "order.alternate"
    result = await agent.tick(original.task_id, SCOPE)
    assert result.status == "resolved"


@pytest.mark.asyncio
async def test_read_retry_exhaustion_has_owner_and_deadline(store):
    async def transient(_request):
        raise TimeoutError()

    original = task()
    await store.create(original)
    agent = await agent_for(store, available=["order.live"], handler=transient)
    for _ in range(3):
        result = await agent.tick(original.task_id, SCOPE)
        if result.status == "waiting_external":
            await wake_task(store, await retry_due(store, original.task_id))
    result = await agent.tick(original.task_id, SCOPE)
    assert result.calls_used == 3
    assert result.status == "waiting_external"
    assert result.wake_condition == "owner_review:no_feasible_action"
    assert result.owner == "support"
    assert result.review_at is not None


@pytest.mark.asyncio
async def test_unknown_write_is_followed_by_read_reconciliation(store):
    writes = []

    async def lost_response(request):
        writes.append(request.key)
        raise TimeoutError()

    async def observe(_task):
        return environment("refund.submit", "refund.status")

    original = task()
    original.goal = "Refund settled to original payment method"
    original.completion_condition = "Original request, amount and currency settled"
    await store.create(original)
    registry = OperationRegistry(
        [
            operation("refund.submit", lost_response, effect="write"),
            replace(operation("refund.status", refund_status), input_schema=RefundStatusInput),
        ]
    )
    policy = AgentPolicy(
        observe=observe,
        propose=refund_candidates,
        verify=lambda task, env: any(e.data == REFUND_RECEIPT for e in task.evidence),
    )
    agent = ServiceAgent(store, registry, policy)
    result = await agent.tick(original.task_id, SCOPE)
    assert result.status == "waiting_external"
    await wake_task(
        store,
        VerifiedWakeup(task_id=original.task_id, scope=SCOPE, condition=result.wake_condition),
    )
    result = await agent.tick(original.task_id, SCOPE)
    assert result.decisions[-1].selected == "refund.status"
    result = await agent.tick(original.task_id, SCOPE)
    assert result.status == "resolved"
    assert writes == ["refund.submit"]


@pytest.mark.asyncio
async def test_ledger_failure_prevents_external_write(store, monkeypatch):
    invoked = []

    async def handler(request):
        invoked.append(request.key)
        return await success(request)

    async def broken_save(_task):
        raise OSError("disk full")

    original = task()
    await store.create(original)
    monkeypatch.setattr(store, "save", broken_save)
    executor = Executor(
        OperationRegistry([operation("order.write", handler, effect="write")]), store
    )
    with pytest.raises(OSError):
        await executor.execute(original, call("order.write"), env=environment("order.write"))
    assert invoked == []


@pytest.mark.asyncio
async def test_checkpoint_failure_after_write_does_not_replay(store, monkeypatch):
    invoked = []

    async def handler(request):
        invoked.append(request.key)
        return await success(request)

    original = task()
    await store.create(original)
    real_save = store.save

    async def fail_receipt(task):
        if task.ledger[-1].receipt is not None:
            raise OSError("receipt commit failed")
        await real_save(task)

    monkeypatch.setattr(store, "save", fail_receipt)
    executor = Executor(
        OperationRegistry([operation("order.write", handler, effect="write")]), store
    )
    with pytest.raises(OSError):
        await executor.execute(original, call("order.write"), env=environment("order.write"))
    restored = await store.load(original.task_id, SCOPE)
    assert restored.ledger[-1].status == "running"
    monkeypatch.setattr(store, "save", real_save)
    with pytest.raises(ValueError, match="reconcile_required"):
        await executor.execute(restored, call("order.write"), env=environment("order.write"))
    assert invoked == ["request-1"]


@pytest.mark.asyncio
async def test_two_workers_only_one_external_write(store):
    import asyncio

    invoked = []

    async def handler(request):
        invoked.append(request.key)
        return await success(request)

    original = task()
    await store.create(original)
    snapshots = [await store.load(original.task_id, SCOPE) for _ in range(2)]
    executor = Executor(
        OperationRegistry([operation("order.write", handler, effect="write")]), store
    )
    results = await asyncio.gather(
        *[
            executor.execute(snapshot, call("order.write"), env=environment("order.write"))
            for snapshot in snapshots
        ],
        return_exceptions=True,
    )
    assert sum(isinstance(result, TaskConflict) for result in results) == 1
    assert invoked == ["request-1"]


@pytest.mark.asyncio
async def test_invalid_planner_output_becomes_owned_failure(store):
    async def observe(_task):
        return environment("order.live")

    async def invalid(_task, _env):
        return [{"operation_id": "arbitrary.command"}]

    original = task()
    await store.create(original)
    agent = ServiceAgent(
        store,
        OperationRegistry([]),
        AgentPolicy(
            observe=observe,
            propose=invalid,
            verify=lambda task, env: False,
        ),
    )
    result = await agent.tick(original.task_id, SCOPE)
    assert result.status == "waiting_external"
    assert result.recovery_signals[-1].operation_id == "policy.propose"
    assert result.calls_used == 0


@pytest.mark.asyncio
async def test_second_worker_does_not_interrupt_live_operation(store):
    import asyncio

    entered, release = asyncio.Event(), asyncio.Event()

    async def slow(request):
        entered.set()
        await release.wait()
        return await success(request)

    original = task()
    await store.create(original)
    agent = await agent_for(store, available=["order.live"], handler=slow)
    worker = asyncio.create_task(agent.tick(original.task_id, SCOPE))
    try:
        await asyncio.wait_for(entered.wait(), timeout=1)
        second = await agent.tick(original.task_id, SCOPE)
        assert second.status == "active"
        assert second.ledger[-1].status == "running"
        assert second.recovery_signals == []
    finally:
        release.set()
        await worker
    result = await agent.tick(original.task_id, SCOPE)
    assert result.status == "resolved"
    assert result.calls_used == 1
