"""P5 (M6): experience memory replays only successful paths as re-validated hints."""

import pytest

from app.services.agent.memory.experience import ExperiencePath, ExperienceStore
from app.services.agent.service.contracts import Candidate, OperationCall
from app.services.agent.service.driver import advance
from app.services.agent.service.registry import OperationRegistry
from app.services.agent.service.runtime import AgentPolicy, ServiceAgent
from tests.unit.test_service_agent import SCOPE, environment, operation, store, success, task

__all__ = ["store"]

GOAL = "order_status"
OPERATION = "order.read"
OTHER_GOAL = "refund_request"
CONDITIONS = {"channel": "chat"}
OTHER_CONDITIONS = {"channel": "email"}


def success_path(**overrides):
    body = {
        "goal": GOAL,
        "conditions": dict(CONDITIONS),
        "operation_id": OPERATION,
        "task_id": "task-1",
        "outcome": "success",
    }
    body.update(overrides)
    return ExperiencePath(**body)


@pytest.mark.asyncio
async def test_successful_paths_are_suggested_with_revalidation(store):
    experience = ExperienceStore(store.sessions)
    await experience.record(SCOPE, success_path())
    hints = await experience.suggest(SCOPE, goal=GOAL, conditions=dict(CONDITIONS))
    assert len(hints) == 1
    assert hints[0].operation_id == OPERATION
    assert hints[0].requires_revalidation is True


@pytest.mark.asyncio
async def test_failed_paths_are_not_suggested(store):
    experience = ExperienceStore(store.sessions)
    await experience.record(SCOPE, success_path(outcome="failure"))
    assert await experience.suggest(SCOPE, goal=GOAL, conditions=dict(CONDITIONS)) == []


@pytest.mark.asyncio
async def test_goal_and_condition_mismatch_yield_no_hints(store):
    experience = ExperienceStore(store.sessions)
    await experience.record(SCOPE, success_path())
    assert await experience.suggest(SCOPE, goal=OTHER_GOAL, conditions=dict(CONDITIONS)) == []
    assert await experience.suggest(SCOPE, goal=GOAL, conditions=dict(OTHER_CONDITIONS)) == []
    superset = {**CONDITIONS, "region": "cn"}
    assert len(await experience.suggest(SCOPE, goal=GOAL, conditions=superset)) == 1


@pytest.mark.asyncio
async def test_hint_candidates_still_pass_precondition_gate(store):
    experience = ExperienceStore(store.sessions)
    await experience.record(SCOPE, success_path())
    hints = await experience.suggest(SCOPE, goal=GOAL, conditions=dict(CONDITIONS))
    invoked = []

    async def handler(request):
        invoked.append(request)
        return await success(request)

    async def observe(_task):
        return environment(OPERATION)

    async def propose(task, _env):
        return [
            Candidate(
                call=OperationCall(
                    operation_id=hint.operation_id,
                    key=f"hint-{task.calls_used}",
                    arguments={"order_id": "not-owned"},
                ),
                reason="experience hint",
            )
            for hint in hints
        ]

    agent = ServiceAgent(
        store,
        OperationRegistry([operation(OPERATION, handler)]),
        AgentPolicy(observe=observe, propose=propose, verify=lambda t, e: False),
    )
    original = task()
    await store.create(original)
    result = await advance(agent, original.task_id, scope=SCOPE)
    assert invoked == []
    assert result.decisions[0].rejected[OPERATION] == "precondition_failed"
