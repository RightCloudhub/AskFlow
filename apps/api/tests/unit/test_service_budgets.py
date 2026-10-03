"""P4 (M5): decision metadata, task budgets and no-progress guards."""

from datetime import UTC, datetime, timedelta

import pytest

from app.services.agent.service.contracts import Candidate, OperationCall, Receipt
from app.services.agent.service.driver import advance
from app.services.agent.service.registry import OperationRegistry
from app.services.agent.service.runtime import AgentPolicy, ServiceAgent
from tests.unit.test_service_agent import SCOPE, environment, operation, store, success, task

__all__ = ["store"]

ORDER_READ = "order.read"
BUDGET_COST = 3.0
MAX_COST = 5.0
NO_PROGRESS_LIMIT = 2
DEADLINE_MINUTES_AGO = 1
EXPECTED_RESULT = "order status observed"
STOP_CONDITION = "evidence_fresh"


def never(_task, _env):
    return False


def has_evidence(task, _env):
    return bool(task.evidence)


def budget_agent(store, *, ops, propose, verify=never):
    async def observe(_task):
        return environment(*(op.operation_id for op in ops))

    return ServiceAgent(
        store, OperationRegistry(ops), AgentPolicy(observe=observe, propose=propose, verify=verify)
    )


def read_candidate(task, *, cost=None, expected_result=None, stop_conditions=None):
    return Candidate(
        call=OperationCall(
            operation_id=ORDER_READ,
            key=f"attempt-{task.calls_used}",
            arguments={"order_id": "owned"},
        ),
        reason="read the order",
        cost=cost,
        expected_result=expected_result,
        stop_conditions=stop_conditions or [],
    )


@pytest.mark.asyncio
async def test_decision_records_expected_result_and_stop_conditions(store):
    async def propose(task, _env):
        return [
            read_candidate(task, expected_result=EXPECTED_RESULT, stop_conditions=[STOP_CONDITION])
        ]

    agent = budget_agent(
        store, ops=[operation(ORDER_READ, success)], propose=propose, verify=has_evidence
    )
    original = task()
    await store.create(original)
    result = await advance(agent, original.task_id, scope=SCOPE)
    assert result.decisions[0].expected_result == EXPECTED_RESULT
    assert result.decisions[0].stop_conditions == [STOP_CONDITION]


@pytest.mark.asyncio
async def test_decision_defaults_keep_legacy_shape(store):
    async def propose(task, _env):
        return [read_candidate(task)]

    agent = budget_agent(
        store, ops=[operation(ORDER_READ, success)], propose=propose, verify=has_evidence
    )
    original = task()
    await store.create(original)
    result = await advance(agent, original.task_id, scope=SCOPE)
    assert result.decisions[0].expected_result is None
    assert result.decisions[0].stop_conditions == []


@pytest.mark.asyncio
async def test_expired_deadline_stops_execution(store):
    invoked = []

    async def handler(request):
        invoked.append(request)
        return await success(request)

    async def propose(task, _env):
        return [read_candidate(task)]

    agent = budget_agent(store, ops=[operation(ORDER_READ, handler)], propose=propose)
    original = task()
    original.deadline = datetime.now(UTC) - timedelta(minutes=DEADLINE_MINUTES_AGO)
    await store.create(original)
    result = await advance(agent, original.task_id, scope=SCOPE)
    assert result.status == "waiting_external"
    assert result.wake_condition == "owner_review:deadline_exceeded"
    assert invoked == []
    assert result.calls_used == 0


@pytest.mark.asyncio
async def test_cost_budget_blocks_second_spend(store):
    async def propose(task, _env):
        return [read_candidate(task, cost=BUDGET_COST)]

    agent = budget_agent(store, ops=[operation(ORDER_READ, success)], propose=propose)
    original = task()
    original.max_cost = MAX_COST
    await store.create(original)
    result = await advance(agent, original.task_id, scope=SCOPE)
    assert result.calls_used == 1
    assert result.cost_used == BUDGET_COST
    assert result.wake_condition == "owner_review:task_budget_exhausted"
    assert result.decisions[-1].rejected[ORDER_READ] == "budget_exceeded"


@pytest.mark.asyncio
async def test_repeated_no_progress_cycles_stop_the_task(store):
    async def bare_success(_request):
        return Receipt(status="succeeded")

    async def propose(task, _env):
        return [read_candidate(task)]

    agent = budget_agent(store, ops=[operation(ORDER_READ, bare_success)], propose=propose)
    original = task()
    original.no_progress_limit = NO_PROGRESS_LIMIT
    await store.create(original)
    result = await advance(agent, original.task_id, scope=SCOPE)
    assert result.wake_condition == "owner_review:no_progress"
    assert result.calls_used == NO_PROGRESS_LIMIT
