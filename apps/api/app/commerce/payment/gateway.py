"""Durable mock provider; future providers implement the same charge/refund/query port."""

import hashlib
import hmac
import json
from datetime import UTC, datetime

from sqlalchemy import select

from app.commerce.account.crypto import digest
from app.commerce.core.errors import MallError
from app.commerce.core.repository import cas, insert_once
from app.commerce.payment.models import GatewayTransaction
from app.core.config import get_settings


def encode(payload: dict) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()


def sign(body: bytes) -> str:
    return hmac.new(get_settings().payment_callback_secret.encode(), body, hashlib.sha256).hexdigest()


def verify(body: bytes, signature: str) -> bool:
    return hmac.compare_digest(sign(body), signature)


class MockGateway:
    async def charge(self, db, request):
        await insert_once(db, GatewayTransaction, values={"request_key": request.request_key,
            "payment_id": request.id, "kind": "charge", "amount_cents": request.external_cents,
            "currency": request.currency, "payer_hash": digest("mock-payer:" + request.user_id)}, unique=["request_key"])
        return await self.query(db, request.request_key)

    async def refund(self, db, request):
        key = "refund:" + request.id
        await insert_once(db, GatewayTransaction, values={"request_key": key,
            "refund_id": request.id, "payment_id": request.payment_id,
            "kind": "refund", "amount_cents": request.external_cents,
            "currency": get_settings().mall_currency, "status": "succeeded",
            "settled_at": datetime.now(UTC)}, unique=["request_key"])
        return await self.query(db, key)

    async def refund_late(self, db, payment):
        key = "late-refund:" + payment.id
        await insert_once(db, GatewayTransaction, values={"request_key": key,
            "payment_id": payment.id, "kind": "late_refund", "amount_cents": payment.external_cents,
            "currency": payment.currency, "status": "succeeded", "settled_at": datetime.now(UTC)},
            unique=["request_key"])
        return await self.query(db, key)

    async def query(self, db, request_key: str):
        row = await db.scalar(select(GatewayTransaction).where(GatewayTransaction.request_key == request_key))
        if row is None:
            raise MallError("gateway_transaction_missing")
        return row

    async def settle(self, db, request_key: str, *, status: str, payer_reference: str = ""):
        row = await self.query(db, request_key)
        if row.status != "pending":
            if row.status != status:
                raise MallError("gateway_outcome_conflict")
            return row
        payer = digest("mock-payer:" + payer_reference) if payer_reference else row.payer_hash
        await cas(db, row, values={"status": status, "settled_at": datetime.now(UTC), "payer_hash": payer})
        return row
