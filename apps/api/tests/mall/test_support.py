"""Internal lookup never trusts a customer ID supplied by an unauthenticated caller."""

import pytest

from app.core.config import get_settings
from .helpers import place, seed, transaction


@pytest.mark.asyncio
async def test_internal_lookup_requires_token_and_owner(mall_runtime, monkeypatch):
    monkeypatch.setenv("ORDER_LOOKUP_TOKEN", "lookup-test-only-token")
    get_settings.cache_clear()
    identity, other = await seed(mall_runtime), await seed(mall_runtime)
    order = await transaction(mall_runtime, lambda db: place(db, identity))
    query = {"order_id": order["id"], "customer_id": identity["user_id"]}
    client = mall_runtime.client
    unauthorized = await client.get("/internal/mall/orders/lookup", params=query)
    assert unauthorized.status_code == 401
    auth = {"Authorization": "Bearer lookup-test-only-token"}
    found = await client.get("/internal/mall/orders/lookup", params=query, headers=auth)
    assert found.json()["status"] == "pending_payment"
    assert found.json()["data_source"] == "mall_database"
    foreign = await client.get("/internal/mall/orders/lookup", params={**query, "customer_id": other["user_id"]}, headers=auth)
    assert foreign.status_code == 404
