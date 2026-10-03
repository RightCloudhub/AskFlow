"""P4 (M5): sourced environment facts drive deterministic, explainable selection."""

from datetime import UTC, datetime, timedelta

import pytest

from app.services.agent.service.contracts import (
    Candidate,
    Environment,
    Operation,
    OperationCall,
    SourcedFact,
)
from app.services.agent.service.driver import advance
from app.services.agent.service.registry import OperationRegistry
from app.services.agent.service.runtime import AgentPolicy, ServiceAgent
from tests.unit.test_service_agent import SCOPE, OrderInput, operation, store, success, task

__all__ = ["store"]

PRIMARY = "order.read"
SECONDARY = "order.confirm"
PERMISSION = "orders.read"
FRESH_MINUTES = 1
EXPIRED_MINUTES = -1
LOW_COST = 2.0
HIGH_COST = 5.0
FAST_MS = 100
SLOW_MS = 500
STABLE = 0.9
FLAKY = 0.5
UTILITY_LOW = 0.2
UTILITY_HIGH = 0.9
ESTIMATOR = "estimator_v1"

SELECTION_CASES = [
    ({"risk": 1}, {"risk": 2}, PRIMARY),
    ({"risk": 2}, {"risk": 1}, SECONDARY),
    ({"cost": LOW_COST}, {"cost": HIGH_COST}, PRIMARY),
    ({"latency_ms": FAST_MS}, {"latency_ms": SLOW_MS}, PRIMARY),
    ({"stability": STABLE}, {"stability": FLAKY}, PRIMARY),
]
UTILITY_CASES = [
    (
        {"utility": UTILITY_LOW, "utility_source": ESTIMATOR, "risk": 1},
        {"utility": UTILITY_HIGH, "utility_source": ESTIMATOR, "risk": 0},
        SECONDARY,
    ),
    ({"utility": UTILITY_HIGH, "risk": 1}, {"risk": 0}, SECONDARY),
    (
        {"utility": UTILITY_HIGH, "risk": 0},
        {"utility": UTILITY_LOW, "utility_source": ESTIMATOR, "risk": 0},
        SECONDARY,
    ),
]
FLIP_CASES = [
    ("channel_health", "ok", "degraded"),
    ("inventory", "in_stock", "out_of_stock"),
    ("queue_duration", "short", "long"),
]


def fact(value, *, expires_in_minutes=FRESH_MINUTES, simulated=False):
    now = datetime.now(UTC)
    return SourcedFact(
        value=value,
        source="connector",
        observed_at=now,
        expires_at=now + timedelta(minutes=expires_in_minutes),
        simulated=simulated,
    )


def env_with(*, sourced=None, preferences=None, available=(PRIMARY, SECONDARY)):
    return Environment(
        scope=SCOPE,
        permissions=frozenset({PERMISSION}),
        available_operations=frozenset(available),
        sourced_facts=sourced or {},
        preferences=preferences or {},
    )


def candidate(name, **fields):
    return Candidate(
        call=OperationCall(operation_id=name, key=f"key-{name}", arguments={"order_id": "owned"}),
        reason="candidate",
        **fields,
    )


def never(_task, _env):
    return False


def selection_agent(store, ops, propose, *, observe=None):
    async def default_observe(_task):
        return env_with()

    return ServiceAgent(
        store,
        OperationRegistry(ops),
        AgentPolicy(observe=observe or default_observe, propose=propose, verify=never),
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("case", SELECTION_CASES)
async def test_deterministic_ordering_without_estimates(store, case):
    better, worse, expected = case

    async def propose(_task, _env):
        return [candidate(PRIMARY, **better), candidate(SECONDARY, **worse)]

    ops = [operation(PRIMARY, success), operation(SECONDARY, success)]
    agent = selection_agent(store, ops, propose)
    original = task()
    await store.create(original)
    result = await advance(agent, original.task_id, scope=SCOPE)
    assert result.decisions[0].selected == expected


@pytest.mark.asyncio
@pytest.mark.parametrize("case", UTILITY_CASES)
async def test_utility_only_counts_when_sourced(store, case):
    better, worse, expected = case

    async def propose(_task, _env):
        return [candidate(PRIMARY, **better), candidate(SECONDARY, **worse)]

    ops = [operation(PRIMARY, success), operation(SECONDARY, success)]
    agent = selection_agent(store, ops, propose)
    original = task()
    await store.create(original)
    result = await advance(agent, original.task_id, scope=SCOPE)
    assert result.decisions[0].selected == expected


def inventory_operation(handler):
    def needs_inventory(_args, env):
        entry = env.sourced_facts.get("inventory")
        return bool(entry) and entry.value == "in_stock"

    return Operation(
        operation_id=PRIMARY,
        version="1",
        effect="read",
        permission=PERMISSION,
        input_schema=OrderInput,
        handler=handler,
        precondition=needs_inventory,
    )


async def probe_fact_selection(store, *, sourced_fact):
    invoked = []

    async def handler(request):
        invoked.append(request)
        return await success(request)

    async def observe(_task):
        return env_with(sourced={"inventory": sourced_fact}, available=(PRIMARY,))

    async def propose(_task, _env):
        return [candidate(PRIMARY)]

    agent = selection_agent(store, [inventory_operation(handler)], propose, observe=observe)
    original = task()
    await store.create(original)
    result = await advance(agent, original.task_id, scope=SCOPE)
    return invoked, result


@pytest.mark.asyncio
async def test_expired_sourced_fact_is_not_used(store):
    invoked, result = await probe_fact_selection(
        store, sourced_fact=fact("in_stock", expires_in_minutes=EXPIRED_MINUTES)
    )
    assert invoked == []
    assert result.status == "waiting_external"
    assert result.decisions[-1].rejected[PRIMARY] == "precondition_failed"


@pytest.mark.asyncio
async def test_simulated_sourced_fact_is_dropped(store):
    invoked, result = await probe_fact_selection(
        store, sourced_fact=fact("in_stock", simulated=True)
    )
    assert invoked == []
    assert result.decisions[-1].rejected[PRIMARY] == "precondition_failed"


@pytest.mark.asyncio
async def test_fresh_sourced_fact_is_used(store):
    invoked, result = await probe_fact_selection(store, sourced_fact=fact("in_stock"))
    assert len(invoked) == 1
    assert result.decisions[0].selected == PRIMARY


@pytest.mark.asyncio
@pytest.mark.parametrize("case", FLIP_CASES)
async def test_fact_change_flips_selection(store, case):
    fact_name, good, bad = case
    holder = {"value": good}

    def prefers_primary(_args, env):
        entry = env.sourced_facts.get(fact_name)
        return bool(entry) and entry.value == good

    primary = Operation(
        operation_id=PRIMARY,
        version="1",
        effect="read",
        permission=PERMISSION,
        input_schema=OrderInput,
        handler=success,
        precondition=prefers_primary,
    )
    ops = [primary, operation(SECONDARY, success)]

    async def observe(_task):
        return env_with(sourced={fact_name: fact(holder["value"])})

    async def propose(_task, _env):
        return [candidate(PRIMARY), candidate(SECONDARY)]

    agent = selection_agent(store, ops, propose, observe=observe)
    first = task()
    await store.create(first)
    first_result = await advance(agent, first.task_id, scope=SCOPE)
    assert first_result.decisions[0].selected == PRIMARY

    holder["value"] = bad
    second = task()
    await store.create(second)
    second_result = await advance(agent, second.task_id, scope=SCOPE)
    assert second_result.decisions[0].selected == SECONDARY
    assert second_result.decisions[0].rejected[PRIMARY] == "precondition_failed"
