"""Refund approval and mock settlement update payment, order and balanced journals."""

import pytest
from sqlalchemy import select

from app.commerce.order.refunds import RefundService
from app.commerce.order.service import OrderService
from app.commerce.payment.compensation import compensate
from app.commerce.payment.models import Payment
from app.commerce.wallet.service import WalletService

from .helpers import headers, transaction
from .test_payment import pending, provider_success


@pytest.mark.asyncio
async def test_partial_refund_to_wallet_settles_once(mall_runtime):
    identity, order, payment = await pending(mall_runtime)
    await provider_success(mall_runtime, payment)
    await transaction(mall_runtime, lambda db: compensate(db, payment["id"]))
    url = "/api/v1/mall/order/orders/" + order["id"] + "/refunds"
    auth = headers(identity, key="partial-refund")
    payload = {"amount_cents": 100, "reason": "test", "destination": "wallet"}
    offered = await mall_runtime.client.post(url, json=payload, headers=auth)
    assert offered.json()["status"] == "needs_confirmation"
    response = await mall_runtime.client.post(url, json={**payload,
        "confirmation_token": offered.json()["confirmation_token"]}, headers=auth)
    assert response.status_code == 200, response.text
    refund_id = response.json()["id"]
    for _ in range(2):
        await transaction(mall_runtime, lambda db: RefundService(db).process(refund_id))
    async with mall_runtime.sessions() as db:
        status = await OrderService(db).get(identity["user_id"], order["id"])
        assert (status["status"], status["refunded_cents"], status["refund_reserved_cents"]) == ("PARTIALLY_REFUNDED", 100, 0)
        assert (await WalletService(db).balance(identity["user_id"]))["available_cents"] == 100
        assert (await db.scalar(select(Payment))).refunded_cents == 100


@pytest.mark.asyncio
async def test_late_receipt_refunds_without_reviving_order(mall_runtime):
    identity, order, payment = await pending(mall_runtime)
    await transaction(mall_runtime, lambda db: OrderService(db).cancel(identity["user_id"], order["id"]))
    await provider_success(mall_runtime, payment)
    for _ in range(3):
        await transaction(mall_runtime, lambda db: compensate(db, payment["id"]))
    async with mall_runtime.sessions() as db:
        status = await OrderService(db).get(identity["user_id"], order["id"])
        assert status["status"] == "CANCELLED"
        result = await db.get(Payment, payment["id"])
        assert result.status == "late_refunded"
        assert result.refunded_cents == payment["external_cents"]
