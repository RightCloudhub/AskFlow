"""Signed callbacks are matched against provider identity, amount and currency."""

import hashlib
import time

from sqlalchemy import select

from app.commerce.core.audit import audit
from app.commerce.core.errors import MallError
from app.commerce.core.events import publish
from app.commerce.core.repository import insert_once
from app.commerce.core.services import service
from app.commerce.payment.gateway import verify
from app.commerce.payment.models import Payment, PaymentCallback
from app.commerce.payment.schemas import Callback
from app.commerce.payment.settlement import settle
from app.core.config import get_settings


async def receive(db, body: bytes, *, signature: str):
    if not verify(body, signature):
        raise MallError("callback_signature_invalid", status=401)
    payload = Callback.model_validate_json(body)
    if abs(time.time() - payload.timestamp) > get_settings().mall_payment_callback_window_seconds:
        raise MallError("callback_expired", status=401)
    row = await db.get(Payment, payload.payment_id)
    if row is None:
        raise MallError("resource_not_found", status=404)
    if row.order_id:
        await service("order", db).get(row.user_id, row.order_id, lock=True)
    row = await db.scalar(select(Payment).where(Payment.id == row.id).with_for_update()
                          .execution_options(populate_existing=True))
    digest = hashlib.sha256(body).hexdigest()
    valid = (payload.amount_cents, payload.currency, payload.transaction_id) == (
        row.external_cents, row.currency, row.provider_ref)
    if not valid:
        await insert_once(db, PaymentCallback, values={"channel": "mock_rejected",
            "transaction_id": digest, "payment_id": row.id, "body_digest": digest,
            "raw_payload": payload.model_dump(), "signature_valid": True,
            "status": "rejected", "error_kind": "amount_or_identity_mismatch"},
            unique=["channel", "transaction_id"])
        await audit(db, actor_id=row.user_id, action="callback_mismatch", resource_id=row.id)
        await publish(db, row, event_type="mall.payment.callback_rejected",
                      payload={"payment_id": row.id, "requires_review": True})
        raise MallError("callback_amount_or_identity_mismatch", persist=True)
    created = await insert_once(db, PaymentCallback, values={"channel": "mock",
        "transaction_id": payload.transaction_id, "payment_id": row.id, "body_digest": digest,
        "raw_payload": payload.model_dump(), "signature_valid": True}, unique=["channel", "transaction_id"])
    callback = await db.scalar(select(PaymentCallback).where(PaymentCallback.channel == "mock",
        PaymentCallback.transaction_id == payload.transaction_id))
    if not created:
        expected = {key: value for key, value in callback.raw_payload.items() if key != "timestamp"}
        actual = payload.model_dump(exclude={"timestamp"})
        if expected != actual:
            raise MallError("callback_conflict")
        return {"status": "accepted", "duplicate": True}
    await settle(db, row, status=payload.status)
    callback.status = "processed"
    await db.flush()
    return {"status": "accepted", "duplicate": False}
