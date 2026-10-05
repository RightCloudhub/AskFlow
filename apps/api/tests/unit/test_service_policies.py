"""P2 (M2): goal→policy resolution replaces worker hardcoding; unknown goals go to review."""

from datetime import UTC, datetime

import pytest

from app.models.service_dispatch import ServiceDispatch
from app.services.agent.service.contracts import Candidate, OperationCall
from app.services.agent.service.driver import advance
from app.services.agent.service.policies import AgentPolicyRegistry, default_policy_registry
from app.services.agent.service.registry import OperationRegistry
from app.services.agent.service.runtime import AgentPolicy, ServiceAgent
from app.workers.service_tasks import run_once
from tests.unit.test_service_agent import (
    SCOPE,
    environment,
    operation,
    store,
    success,
    task,
)

__all__ = ["store"]

TEST_GOAL = "test_goal"
TEST_OPERATION = "order.read"
UNKNOWN_GOAL = "no_such_goal"


def test_default_registry_resolves_order_goal():
    assert default_policy_registry().resolve("order_status") is not None


def test_unknown_goal_has_no_policy():
    assert default_policy_registry().resolve(UNKNOWN_GOAL) is None


def stub_builder(_store, _task):
    return None


def test_duplicate_registration_is_rejected():
    registry = AgentPolicyRegistry()
    registry.register(TEST_GOAL, builder=stub_builder)
    with pytest.raises(ValueError):
        registry.register(TEST_GOAL, builder=stub_builder)


@pytest.mark.asyncio
async def test_second_goal_smoke_resolves_end_to_end(store):
    async def observe(_task):
        return environment(TEST_OPERATION)

    async def propose(_task, _env):
        return [
            Candidate(
                call=OperationCall(
                    operation_id=TEST_OPERATION, key="test-1", arguments={"order_id": "owned"}
                ),
                reason="registered test goal",
            )
        ]

    def verify(task, _env):
        return bool(task.evidence)

    def builder(_store, _task):
        return ServiceAgent(
            _store,
            OperationRegistry([operation(TEST_OPERATION, success)]),
            AgentPolicy(observe=observe, propose=propose, verify=verify),
        )

    registry = AgentPolicyRegistry()
    registry.register(TEST_GOAL, builder)
    original = task()
    original.goal = TEST_GOAL
    original.completion_condition = TEST_GOAL
    await store.create(original)
    agent = registry.resolve(TEST_GOAL)(store, original)
    result = await advance(agent, original.task_id, scope=SCOPE)
    assert result.status == "resolved"


@pytest.mark.asyncio
async def test_worker_routes_unknown_goal_to_owner_review(store):
    original = task()
    original.goal = UNKNOWN_GOAL
    original.completion_condition = UNKNOWN_GOAL
    await store.create(original)
    async with store.sessions.begin() as db:
        db.add(ServiceDispatch(task_id=original.task_id, due_at=datetime.now(UTC)))
    counts = await run_once(sessions=store.sessions)
    assert counts["processed"] == 1
    result = await store.load(original.task_id, SCOPE)
    assert result.status == "waiting_external"
    assert result.wake_condition == "owner_review:unknown_goal"
