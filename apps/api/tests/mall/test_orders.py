"""Checkout idempotency, ownership and Gateway confirmations."""

import asyncio

import pytest
from sqlalchemy import func, select

from app.commerce.order.models import Order

from .helpers import headers, place, seed, transaction


@pytest.mark.asyncio
async def test_concurrent_order_key_has_one_result(mall_runtime):
    identity = await seed(mall_runtime)
    client = mall_runtime.client
    items = {"items": [{"sku_id": identity["sku_id"], "qty": 1}]}
    quote = await client.post("/api/v1/mall/order/checkout", json=items, headers=headers(identity))
    assert quote.status_code == 200, quote.text
    payload = {**items, "checkout_token": quote.json()["checkout_token"]}
    auth = headers(identity, key="one-checkout")
    responses = await asyncio.gather(*(client.post("/api/v1/mall/order/orders", json=payload,
                                                   headers=auth) for _ in range(10)))
    assert {row.status_code for row in responses} == {200}
    assert len({row.json()["id"] for row in responses}) == 1
    async with mall_runtime.sessions() as db:
        assert await db.scalar(select(func.count()).select_from(Order)) == 1


@pytest.mark.asyncio
async def test_foreign_order_is_not_found(mall_runtime):
    owner, stranger = await seed(mall_runtime), await seed(mall_runtime)
    order = await transaction(mall_runtime, lambda db: place(db, owner))
    response = await mall_runtime.client.get("/api/v1/mall/order/orders/" + order["id"], headers=headers(stranger))
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_cancellation_requires_confirmation_and_replays(mall_runtime):
    identity = await seed(mall_runtime)
    order = await transaction(mall_runtime, lambda db: place(db, identity))
    url, auth = "/api/v1/mall/order/orders/" + order["id"] + "/cancel", headers(identity, key="cancel-once")
    payload = {"expected_version": order["version"]}
    first = await mall_runtime.client.post(url, json=payload, headers=auth)
    assert first.json()["status"] == "needs_confirmation"
    confirmed = {**payload, "confirmation_token": first.json()["confirmation_token"]}
    second = await mall_runtime.client.post(url, json=confirmed, headers=auth)
    repeated = await mall_runtime.client.post(url, json=confirmed, headers=auth)
    assert second.json()["status"] == "CANCELLED"
    assert repeated.json() == second.json()
