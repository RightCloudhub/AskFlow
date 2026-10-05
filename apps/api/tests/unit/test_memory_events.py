"""P5 (M6): the task timeline is materialized from transition and ledger references."""

from datetime import UTC, datetime, timedelta

import pytest

from app.services.agent.memory.events import TimelineStore, materialize
from app.services.agent.service.contracts import (
    Evidence,
    LedgerEntry,
    Receipt,
    Scope,
    TaskTransition,
)
from tests.unit.test_service_agent import call, task
from tests.unit.test_service_agent import store as task_store

__all__ = ["task_store"]

CONVERSATION = "conv-1"
OPERATION_KEY = "op-1"
EXPECTED_EVENTS = 2
T0_MINUTES_AGO = 2
T1_MINUTES_AGO = 1
TTL_MINUTES = 1


def timeline_task():
    original = task()
    original.conversation_id = CONVERSATION
    t0 = datetime.now(UTC) - timedelta(minutes=T0_MINUTES_AGO)
    t1 = datetime.now(UTC) - timedelta(minutes=T1_MINUTES_AGO)
    original.transitions = [
        TaskTransition(
            previous="active",
            current="waiting_customer",
            actor_id="agent",
            reason="need_info",
            occurred_at=t0,
        )
    ]
    receipt = Receipt(
        status="succeeded",
        evidence=Evidence(
            operation_id="order.read",
            source="order-api",
            data={"status": "shipped"},
            observed_at=t1,
            expires_at=t1 + timedelta(minutes=TTL_MINUTES),
        ),
    )
    original.ledger = [
        LedgerEntry(
            call=call("order.read", key=OPERATION_KEY),
            operation_version="1",
            status="succeeded",
            receipt=receipt,
        )
    ]
    return original


def test_materialize_orders_transitions_and_operations():
    events = materialize(timeline_task())
    assert [e.kind for e in events] == ["transition", "operation"]
    assert events[0].ref == "transition:0"
    assert events[1].ref == OPERATION_KEY
    assert events[1].summary


def test_materialize_is_deterministic_and_keeps_references_only():
    original = timeline_task()
    events = materialize(original)
    payload = events[1].model_dump()
    assert "data" not in payload
    assert "receipt" not in payload
    assert [e.event_id for e in materialize(original)] == [e.event_id for e in events]


@pytest.mark.asyncio
async def test_timeline_append_is_idempotent_and_scoped(task_store):
    original = timeline_task()
    timeline = TimelineStore(task_store.sessions)
    assert await timeline.append(original) == EXPECTED_EVENTS
    assert await timeline.append(original) == 0
    events = await timeline.list(original.scope, conversation_id=CONVERSATION)
    assert len(events) == EXPECTED_EVENTS
    assert [e.kind for e in events] == ["transition", "operation"]
    other = Scope(organization_id="other", customer_id="other")
    assert await timeline.list(other, conversation_id=CONVERSATION) == []
