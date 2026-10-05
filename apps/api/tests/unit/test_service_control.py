"""Lifecycle changes preserve unsettled operations and invalidate stale workers."""

import pytest

from app.models.handoff import HandoffSession
from app.services.agent.identity import customer_scope
from app.services.agent.service.contracts import LedgerEntry
from app.services.agent.service.control import (
    HandoffAcceptance,
    InvalidTransition,
    accept_handoff,
    cancel_task,
)
from app.services.agent.service.executor import Executor
from app.services.agent.service.registry import OperationRegistry
from app.services.agent.service.store import TaskConflict
from tests.unit.test_service_agent import (
    SCOPE,
    call,
    environment,
    operation,
    store,
    success,
    task,
)

__all__ = ["store"]


@pytest.mark.asyncio
async def test_cancellation_fences_stale_worker(store):
    original = task()
    await store.create(original)
    stale = await store.load(original.task_id, SCOPE)
    cancelled = await cancel_task(
        store,
        original.task_id,
        scope=SCOPE,
        expected_version=0,
        reason="Customer changed their mind",
    )
    assert cancelled.status == "closed_unresolved"
    assert cancelled.transitions[-1].actor_id == SCOPE.customer_id
    called = []

    async def handler(request):
        called.append(request)
        return await success(request)

    executor = Executor(
        OperationRegistry([operation("order.write", handler, effect="write")]), store
    )
    with pytest.raises(TaskConflict):
        await executor.execute(stale, call("order.write"), env=environment("order.write"))
    assert called == []


@pytest.mark.asyncio
async def test_cancel_keeps_unknown_side_effects_for_review(store):
    original = task()
    original.ledger = [
        LedgerEntry(call=call("refund.submit"), operation_version="1", status="unknown")
    ]
    original.calls_used = 1
    await store.create(original)
    result = await cancel_task(
        store, original.task_id, scope=SCOPE, expected_version=0, reason="Cancel request"
    )
    assert result.ledger[0].status == "unknown"
    assert result.calls_used == 1
    assert result.review_at is not None
    assert result.wake_condition == "owner_review:unsettled_operations"


@pytest.mark.asyncio
@pytest.mark.parametrize("state", ["resolved", "handed_off", "closed_unresolved"])
async def test_terminal_states_cannot_be_rewritten_by_customer(store, state):
    original = task()
    original.status = state
    await store.create(original)
    with pytest.raises(InvalidTransition):
        await cancel_task(store, original.task_id, scope=SCOPE, expected_version=0, reason="Cancel")


async def handoff_setup(store, *, state="claimed", claimant="staff", conversation="conversation"):
    original = task()
    original.scope = customer_scope("customer")
    original.conversation_id = "conversation"
    await store.create(original)
    async with store.sessions.begin() as db:
        handoff = HandoffSession(
            user_id="customer", conversation_id=conversation, status=state, claimed_by=claimant
        )
        db.add(handoff)
        await db.flush()
        handoff_id = handoff.id
    return original, HandoffAcceptance(
        task_id=original.task_id, handoff_id=handoff_id, actor_id="staff", expected_version=0
    )


@pytest.mark.asyncio
async def test_verified_handoff_changes_owner_without_resolving_goal(store):
    original, request = await handoff_setup(store)
    result = await accept_handoff(store, request)
    assert result.status == "handed_off"
    assert result.owner == "staff"
    assert result.review_at is not None
    assert result.transitions[-1].reason == f"handoff:{request.handoff_id}"
    with pytest.raises(TaskConflict):
        await store.save(original)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "kwargs",
    [
        {"state": "queued"},
        {"claimant": "different-staff"},
        {"conversation": "other"},
    ],
)
async def test_unverified_handoff_cannot_take_over_task(store, kwargs):
    original, request = await handoff_setup(store, **kwargs)
    with pytest.raises(LookupError):
        await accept_handoff(store, request)
    restored = await store.load(original.task_id, original.scope)
    assert restored.status == "active" and restored.version == 0


@pytest.mark.asyncio
async def test_concurrent_cancel_and_handoff_has_one_winner(store):
    import asyncio

    original, request = await handoff_setup(store)
    outcomes = await asyncio.gather(
        accept_handoff(store, request),
        cancel_task(
            store, original.task_id, scope=original.scope, expected_version=0, reason="cancel"
        ),
        return_exceptions=True,
    )
    assert sum(isinstance(result, (TaskConflict, InvalidTransition)) for result in outcomes) == 1
    restored = await store.load(original.task_id, original.scope)
    assert restored.version == 1
    assert len(restored.transitions) == 1
