"""P3 (M4): handoff.enqueue is idempotent and the task waits for human acceptance."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.models.handoff import HandoffSession
from app.services.agent.domains.handoff import (
    HANDOFF_COMPENSATION,
    HANDOFF_GOAL,
    HANDOFF_OPERATION,
    HANDOFF_PERMISSION,
    handoff_agent,
    handoff_operations,
)
from app.services.agent.service.contracts import Environment, Evidence, OperationCall
from app.services.agent.service.driver import advance
from app.services.agent.service.executor import Executor
from app.services.agent.service.registry import OperationRegistry
from tests.unit.test_service_agent import SCOPE, store, task

__all__ = ["store"]

CONVERSATION = "conv-1"
HANDOFF_ARGS = {
    "conversation_id": CONVERSATION,
    "user_id": SCOPE.customer_id,
    "summary": "客户要求人工处理",
    "intent": "handoff",
}
EVIDENCE_TTL_MINUTES = 1


def handoff_env(*, status):
    return Environment(
        scope=SCOPE,
        permissions=frozenset({HANDOFF_PERMISSION}),
        available_operations=frozenset({HANDOFF_OPERATION}),
        facts={"handoff_status": status},
    )


def handoff_task():
    original = task()
    original.goal = HANDOFF_GOAL
    original.completion_condition = HANDOFF_GOAL
    original.conversation_id = CONVERSATION
    original.inputs = dict(HANDOFF_ARGS)
    return original


@pytest.mark.asyncio
async def test_handoff_contract_declares_write_and_compensation(store):
    ops = {op.operation_id: op for op in handoff_operations(store.sessions)}
    op = ops[HANDOFF_OPERATION]
    assert op.effect == "write"
    assert op.permission == HANDOFF_PERMISSION
    assert op.compensation == HANDOFF_COMPENSATION


@pytest.mark.asyncio
async def test_enqueue_converges_on_open_session(store):
    executor = Executor(OperationRegistry(handoff_operations(store.sessions)), store)
    original = handoff_task()
    await store.create(original)
    env = handoff_env(status="queued")
    first = await executor.execute(
        original,
        OperationCall(operation_id=HANDOFF_OPERATION, key="h-1", arguments=dict(HANDOFF_ARGS)),
        env=env,
    )
    assert first.status == "succeeded"
    handoff_id = first.evidence.data["handoff_id"]
    restored = await store.load(original.task_id, SCOPE)
    second = await executor.execute(
        restored,
        OperationCall(operation_id=HANDOFF_OPERATION, key="h-2", arguments=dict(HANDOFF_ARGS)),
        env=env,
    )
    assert second.evidence.data["handoff_id"] == handoff_id
    async with store.sessions() as db:
        assert len(list(await db.scalars(select(HandoffSession)))) == 1


@pytest.mark.asyncio
async def test_task_waits_without_reenqueueing(store):
    async def observe(_task):
        return handoff_env(status="queued")

    agent = handoff_agent(store, observe)
    original = handoff_task()
    await store.create(original)
    result = await advance(agent, original.task_id, scope=SCOPE)
    assert result.status == "waiting_external"
    assert result.calls_used == 1
    async with store.sessions() as db:
        assert len(list(await db.scalars(select(HandoffSession)))) == 1


@pytest.mark.asyncio
async def test_human_acceptance_resolves_the_task(store):
    original = handoff_task()
    observed_at = datetime.now(UTC)
    original.evidence = [
        Evidence(
            operation_id=HANDOFF_OPERATION,
            source="handoff_store",
            data={"handoff_id": "h-1", "status": "queued"},
            observed_at=observed_at,
            expires_at=observed_at + timedelta(minutes=EVIDENCE_TTL_MINUTES),
        )
    ]

    async def observe(_task):
        return handoff_env(status="claimed")

    agent = handoff_agent(store, observe)
    await store.create(original)
    result = await advance(agent, original.task_id, scope=SCOPE)
    assert result.status == "resolved"
    assert result.calls_used == 0
