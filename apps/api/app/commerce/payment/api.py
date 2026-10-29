"""Payment creation, durable mock outcomes and HMAC callback ingress."""

import time

from fastapi import APIRouter, Request

from app.commerce.account.mfa import require_step_up
from app.commerce.core.commands import command
from app.commerce.core.deps import MallContext, MallDb
from app.commerce.core.errors import MallError
from app.commerce.core.repository import owned
from app.commerce.payment import schemas
from app.commerce.payment.callbacks import receive
from app.commerce.payment.gateway import encode, sign
from app.commerce.payment.models import Payment
from app.commerce.payment.service import PaymentService
from app.core.config import get_settings

CALLBACK_MAX_BYTES = 16384
router = APIRouter()


@router.post("")
async def start(payload: schemas.StartPayment, ctx: MallContext):
    from app.commerce.core.services import service

    order = await service("order", ctx.db).get(ctx.user.id, payload.order_id)
    if order["total_cents"] >= get_settings().mall_payment_step_up_cents:
        require_step_up(ctx, payload.step_up_token, purpose="payment")
    return await command(ctx, "payment.start", payload=payload,
                         action=lambda: PaymentService(ctx.db).start(ctx.user.id, payload))


@router.get("/{payment_id}")
async def payment(payment_id: str, ctx: MallContext):
    return await PaymentService(ctx.db).get(ctx.user.id, payment_id)


@router.post("/callbacks/mock")
async def callback(request: Request, db: MallDb):
    body = bytearray()
    async for part in request.stream():
        body.extend(part)
        if len(body) > CALLBACK_MAX_BYTES:
            raise MallError("payload_too_large", status=413)
    return await receive(db, bytes(body), signature=request.headers.get("x-payment-signature", ""))


@router.post("/{payment_id}/mock")
async def mock(payment_id: str, payload: schemas.MockOutcome, ctx: MallContext):
    if not get_settings().mall_payment_mock_enabled:
        raise MallError("resource_not_found", status=404)

    async def perform():
        row = await owned(ctx.db, Payment, owner_id=ctx.user.id, resource_id=payment_id)
        remote = await PaymentService(ctx.db).gateway.settle(ctx.db, row.request_key, status=payload.status)
        body = encode({"payment_id": row.id, "transaction_id": remote.id, "status": remote.status,
            "amount_cents": remote.amount_cents, "currency": remote.currency,
            "timestamp": int(time.time())})
        if payload.deliver_callback:
            await receive(ctx.db, body, signature=sign(body))
        return {"payment_id": row.id, "provider_status": remote.status, "data_source": "mock"}

    return await command(ctx, "payment.mock:" + payment_id, payload=payload, action=perform)
