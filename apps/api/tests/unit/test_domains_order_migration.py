"""P2 (M3): the order domain lives at its new module path with unchanged behavior."""

import pytest

from app.services.agent.domains.order import ORDER_GOAL, ORDER_OPERATION, order_agent
from app.services.agent.service.contracts import Environment
from app.services.agent.service.driver import advance
from tests.unit.test_service_agent import SCOPE, store, task

__all__ = ["store"]


async def observation(_task):
    return Environment(
        scope=SCOPE,
        permissions=frozenset({"orders.read"}),
        available_operations=frozenset({ORDER_OPERATION}),
        facts={"order_owners": {"owned": SCOPE.customer_id}},
    )


@pytest.mark.asyncio
async def test_migrated_order_domain_resolves_with_live_connector(store, monkeypatch):
    async def connector(_args):
        return {
            "status": "ok",
            "order_id": "owned",
            "data_source": "webhook",
            "data": {"status": "shipped"},
        }

    monkeypatch.setattr("app.services.agent.domains.order.search_order", connector)
    original = task()
    original.inputs = {"order_id": "owned"}
    original.completion_condition = ORDER_GOAL
    await store.create(original)
    result = await advance(order_agent(store, observation), original.task_id, scope=SCOPE)
    assert result.status == "resolved"
    assert result.calls_used == 1
    assert result.evidence[-1].operation_id == ORDER_OPERATION
