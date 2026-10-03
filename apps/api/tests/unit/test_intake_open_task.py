"""P1 (M1): goal task creation is atomic, deduplicated and gated by the takeover list."""

from dataclasses import dataclass

import pytest
from sqlalchemy import select

from app.models.service_dispatch import ServiceDispatch
from app.models.service_task import ServiceTask
from app.services.agent.intake.goals import GOAL_ORDER_STATUS, GOAL_TICKET_RESOLUTION, dedup_key
from app.services.agent.intake.judge import IntakeDecision
from app.services.agent.intake.open_task import open_goal_task
from tests.unit.test_service_agent import store

__all__ = ["store"]

CONVERSATION = "conv-1"
ORDER_ID = "ORD202401010001"


@dataclass
class Conversation:
    id: str
    user_id: str
    status: str = "active"


def decision(goal, *, object_key=None, verdict="goal"):
    return IntakeDecision(
        verdict=verdict, goal=goal, object_key=object_key, confidence=1.0, reason="test"
    )


@pytest.mark.asyncio
async def test_order_goal_creates_task_and_dispatch_together(store):
    conversation = Conversation(id=CONVERSATION, user_id="customer")
    async with store.sessions() as db:
        task = await open_goal_task(
            db, conversation, decision(GOAL_ORDER_STATUS, object_key=ORDER_ID)
        )
        await db.commit()
    assert task is not None
    expected_id = dedup_key(
        conversation_id=CONVERSATION, goal=GOAL_ORDER_STATUS, object_key=ORDER_ID
    )
    assert task.task_id == expected_id
    assert task.inputs == {"order_id": ORDER_ID}
    assert task.completion_condition == GOAL_ORDER_STATUS
    async with store.sessions() as db:
        assert await db.get(ServiceTask, expected_id) is not None
        assert await db.get(ServiceDispatch, expected_id) is not None


@pytest.mark.asyncio
async def test_resend_returns_existing_task_without_duplicate(store):
    conversation = Conversation(id=CONVERSATION, user_id="customer")
    async with store.sessions() as db:
        first = await open_goal_task(
            db, conversation, decision(GOAL_ORDER_STATUS, object_key=ORDER_ID)
        )
        await db.commit()
    async with store.sessions() as db:
        again = await open_goal_task(
            db, conversation, decision(GOAL_ORDER_STATUS, object_key=ORDER_ID)
        )
        await db.commit()
    assert again.task_id == first.task_id
    async with store.sessions() as db:
        assert len(list(await db.scalars(select(ServiceTask)))) == 1


@pytest.mark.asyncio
async def test_goal_outside_takeover_list_falls_back_to_legacy(store, monkeypatch):
    monkeypatch.setenv("SERVICE_TASKS_GOALS", GOAL_ORDER_STATUS)
    conversation = Conversation(id=CONVERSATION, user_id="customer")
    async with store.sessions() as db:
        task = await open_goal_task(db, conversation, decision(GOAL_TICKET_RESOLUTION))
        await db.commit()
    assert task is None
    async with store.sessions() as db:
        assert list(await db.scalars(select(ServiceTask))) == []


@pytest.mark.asyncio
async def test_allowlisted_goal_creates_task(store, monkeypatch):
    monkeypatch.setenv("SERVICE_TASKS_GOALS", f"{GOAL_ORDER_STATUS},{GOAL_TICKET_RESOLUTION}")
    conversation = Conversation(id=CONVERSATION, user_id="customer")
    async with store.sessions() as db:
        task = await open_goal_task(db, conversation, decision(GOAL_TICKET_RESOLUTION))
        await db.commit()
    assert task is not None
    assert task.goal == GOAL_TICKET_RESOLUTION


@pytest.mark.asyncio
async def test_non_goal_verdict_creates_nothing(store):
    conversation = Conversation(id=CONVERSATION, user_id="customer")
    async with store.sessions() as db:
        task = await open_goal_task(db, conversation, decision(None, verdict="answer"))
        await db.commit()
    assert task is None
    async with store.sessions() as db:
        assert list(await db.scalars(select(ServiceTask))) == []
