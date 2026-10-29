"""Real mock gateway outcomes, tamper rejection and lost-callback compensation."""

import asyncio
import time

import pytest
from sqlalchemy import func, select

from app.commerce.payment.compensation import compensate
from app.commerce.payment.gateway import MockGateway, encode, sign
from app.commerce.payment.models import PaymentCallback
from app.commerce.payment.schemas import StartPayment
from app.commerce.payment.service import PaymentService
from app.commerce.wallet.models import JournalEntry

from .helpers import headers, place, seed, transaction


async def pending(runtime):
    identity = await seed(runtime)
    order = await transaction(runtime, lambda db: place(db, identity))
    payment = await transaction(runtime, lambda db: PaymentService(db).start(identity["user_id"],
        StartPayment(order_id=order["id"])))
    return identity, order, payment


async def provider_success(runtime, payment):
    return await transaction(runtime, lambda db: MockGateway().settle(db, "order:" + payment["order_id"],
                                                                    status="succeeded"))


def callback_body(payment, *, amount=None):
    return encode({"payment_id": payment["id"], "transaction_id": payment["provider_ref"],
        "amount_cents": payment["external_cents"] if amount is None else amount,
        "currency": "CNY", "status": "succeeded", "timestamp": int(time.time())})


@pytest.mark.asyncio
async def test_hundred_callbacks_settle_once(mall_runtime):
    _identity, _order, payment = await pending(mall_runtime)
    await provider_success(mall_runtime, payment)
    body = callback_body(payment)
    responses = await asyncio.gather(*(mall_runtime.client.post("/api/v1/mall/payment/callbacks/mock",
        content=body, headers={"X-Payment-Signature": sign(body)}) for _ in range(100)))
    assert {result.status_code for result in responses} == {200}
    async with mall_runtime.sessions() as db:
        assert await db.scalar(select(func.count()).select_from(PaymentCallback)) == 1
        assert await db.scalar(select(func.count()).select_from(JournalEntry)) == 1


@pytest.mark.asyncio
async def test_signed_wrong_amount_is_rejected_and_retained(mall_runtime):
    identity, order, payment = await pending(mall_runtime)
    body = callback_body(payment, amount=1)
    response = await mall_runtime.client.post("/api/v1/mall/payment/callbacks/mock", content=body,
                                             headers={"X-Payment-Signature": sign(body)})
    assert response.status_code == 409
    detail = await mall_runtime.client.get("/api/v1/mall/order/orders/" + order["id"], headers=headers(identity))
    assert detail.json()["status"] == "PENDING_PAYMENT"
    async with mall_runtime.sessions() as db:
        rejection = await db.scalar(select(PaymentCallback))
        assert rejection.status == "rejected"
        assert await db.scalar(select(func.count()).select_from(JournalEntry)) == 0


@pytest.mark.asyncio
async def test_lost_callback_is_compensated(mall_runtime):
    identity, order, payment = await pending(mall_runtime)
    await provider_success(mall_runtime, payment)
    await transaction(mall_runtime, lambda db: compensate(db, payment["id"]))
    detail = await mall_runtime.client.get("/api/v1/mall/order/orders/" + order["id"], headers=headers(identity))
    assert detail.json()["status"] == "PAID"


@pytest.mark.asyncio
async def test_forged_callback_is_rejected(mall_runtime):
    _identity, _order, payment = await pending(mall_runtime)
    response = await mall_runtime.client.post("/api/v1/mall/payment/callbacks/mock",
        content=callback_body(payment), headers={"X-Payment-Signature": "forged"})
    assert response.status_code == 401


@pytest.mark.asyncio
@pytest.mark.parametrize("body", [b"{", b'{"amount_cents": 1.5}', b"[]"])
async def test_signed_malformed_payload_is_rejected(mall_runtime, body):
    response = await mall_runtime.client.post("/api/v1/mall/payment/callbacks/mock",
        content=body, headers={"X-Payment-Signature": sign(body)})
    assert response.status_code == 422
    async with mall_runtime.sessions() as db:
        assert await db.scalar(select(func.count()).select_from(JournalEntry)) == 0
