"""P3 (M4): ticket.create is a write operation with convergence and declared compensation."""

import pytest
from sqlalchemy import select

from app.models.ticket import Ticket
from app.services.agent.domains.ticket import (
    TICKET_COMPENSATION,
    TICKET_GOAL,
    TICKET_OPERATION,
    TICKET_PERMISSION,
    ticket_agent,
    ticket_operations,
)
from app.services.agent.service.contracts import Environment, OperationCall
from app.services.agent.service.driver import advance
from app.services.agent.service.executor import Executor
from app.services.agent.service.registry import OperationRegistry
from tests.unit.test_service_agent import SCOPE, store, task

__all__ = ["store"]

CONVERSATION = "conv-1"
TICKET_ARGS = {
    "conversation_id": CONVERSATION,
    "user_id": SCOPE.customer_id,
    "title": "页面报错",
    "description": "点击后 500",
    "ticket_type": "fault_report",
    "priority": "high",
}


def ticket_env():
    return Environment(
        scope=SCOPE,
        permissions=frozenset({TICKET_PERMISSION}),
        available_operations=frozenset({TICKET_OPERATION}),
    )


def ticket_task():
    original = task()
    original.goal = TICKET_GOAL
    original.completion_condition = TICKET_GOAL
    original.conversation_id = CONVERSATION
    original.inputs = dict(TICKET_ARGS)
    return original


def ticket_executor(store):
    return Executor(OperationRegistry(ticket_operations(store.sessions)), store)


@pytest.mark.asyncio
async def test_ticket_contract_declares_write_boundary(store):
    ops = {op.operation_id: op for op in ticket_operations(store.sessions)}
    op = ops[TICKET_OPERATION]
    assert op.effect == "write"
    assert op.permission == TICKET_PERMISSION
    assert op.compensation == TICKET_COMPENSATION


@pytest.mark.asyncio
async def test_ticket_create_converges_on_open_ticket(store):
    executor = ticket_executor(store)
    original = ticket_task()
    await store.create(original)
    env = ticket_env()
    first = await executor.execute(
        original,
        OperationCall(operation_id=TICKET_OPERATION, key="t-1", arguments=dict(TICKET_ARGS)),
        env=env,
    )
    assert first.status == "succeeded"
    ticket_id = first.evidence.data["ticket_id"]
    restored = await store.load(original.task_id, SCOPE)
    second = await executor.execute(
        restored,
        OperationCall(operation_id=TICKET_OPERATION, key="t-2", arguments=dict(TICKET_ARGS)),
        env=env,
    )
    assert second.evidence.data["ticket_id"] == ticket_id
    async with store.sessions() as db:
        assert len(list(await db.scalars(select(Ticket)))) == 1


@pytest.mark.asyncio
async def test_ticket_precondition_blocks_other_customer(store):
    executor = ticket_executor(store)
    original = ticket_task()
    await store.create(original)
    stolen = {**TICKET_ARGS, "user_id": "someone-else"}
    with pytest.raises(PermissionError, match="precondition_failed"):
        await executor.execute(
            original,
            OperationCall(operation_id=TICKET_OPERATION, key="t-3", arguments=stolen),
            env=ticket_env(),
        )
    async with store.sessions() as db:
        assert list(await db.scalars(select(Ticket))) == []


@pytest.mark.asyncio
async def test_ticket_goal_resolves_after_creation(store):
    async def observe(_task):
        return ticket_env()

    agent = ticket_agent(store, observe)
    original = ticket_task()
    await store.create(original)
    result = await advance(agent, original.task_id, scope=SCOPE)
    assert result.status == "resolved"
    assert result.calls_used == 1
    assert result.evidence[-1].operation_id == TICKET_OPERATION
