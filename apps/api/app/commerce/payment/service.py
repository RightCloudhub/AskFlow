"""Payments lock orders before wallet accounts; provider identities are durable."""

from datetime import UTC, datetime

from sqlalchemy import select

from app.commerce.core.errors import MallError
from app.commerce.core.repository import cas, owned
from app.commerce.core.schemas import view
from app.commerce.core.services import enabled, service
from app.commerce.payment.gateway import MockGateway
from app.commerce.payment.contracts import RefundInstruction, RefundReceipt
from app.commerce.payment.models import Payment
from app.core.config import get_settings

PAYMENT_FIELDS = ("id", "order_id", "topup_id", "method", "currency", "amount_cents",
                  "wallet_cents", "external_cents", "refunded_cents", "status", "provider_ref", "version")


class PaymentService:
    def __init__(self, db):
        self.db, self.gateway = db, MockGateway()

    async def get(self, user_id: str, payment_id: str):
        row = await owned(self.db, Payment, owner_id=user_id, resource_id=payment_id)
        return view(row, PAYMENT_FIELDS)

    async def unfinished(self, user_id: str):
        return bool(await self.db.scalar(select(Payment.id).where(Payment.user_id == user_id,
            Payment.status == "pending").limit(1)))

    async def start(self, user_id: str, payload):
        order = await service("order", self.db).get(user_id, payload.order_id, lock=True)
        prior = await self.db.scalar(select(Payment).where(Payment.order_id == order["id"]))
        if prior:
            return view(prior, PAYMENT_FIELDS)
        if order["status"] != "PENDING_PAYMENT" or datetime.fromisoformat(order["expires_at"]) <= datetime.now(UTC):
            raise MallError("order_not_payable")
        wallet = order["total_cents"] if payload.method == "wallet" else payload.wallet_cents
        if wallet > order["total_cents"] or (payload.method == "mock" and wallet):
            raise MallError("payment_amount_invalid", status=422)
        external = order["total_cents"] - wallet
        if external and not get_settings().mall_payment_mock_enabled:
            raise MallError("payment_gateway_unavailable", status=503)
        row = Payment(order_id=order["id"], user_id=user_id, method=payload.method,
            currency=order["currency"], amount_cents=order["total_cents"], wallet_cents=wallet,
            external_cents=external, request_key="order:" + order["id"], status="pending")
        self.db.add(row)
        await self.db.flush()
        if wallet:
            await service("wallet", self.db).freeze(user_id, wallet, key="freeze:" + row.id)
        if external:
            gateway = await self.gateway.charge(self.db, row)
            row.provider_ref = gateway.id
        else:
            from app.commerce.payment.settlement import settle

            await settle(self.db, row, status="succeeded")
        await self.db.flush()
        return view(row, PAYMENT_FIELDS)

    async def start_topup(self, user_id: str, topup):
        if not get_settings().mall_payment_mock_enabled:
            raise MallError("payment_gateway_unavailable", status=503)
        row = Payment(user_id=user_id, topup_id=topup["id"], method="mock", status="pending",
            amount_cents=topup["amount_cents"], external_cents=topup["amount_cents"], wallet_cents=0,
            currency=topup["currency"], request_key="topup:" + topup["id"])
        self.db.add(row)
        await self.db.flush()
        remote = await self.gateway.charge(self.db, row)
        row.provider_ref = remote.id
        return view(row, PAYMENT_FIELDS)

    async def cancel_order(self, user_id: str, order_id: str):
        row = await self.db.scalar(select(Payment).where(Payment.order_id == order_id,
            Payment.user_id == user_id).with_for_update().execution_options(populate_existing=True))
        if row is None or row.status != "pending":
            return
        if row.wallet_cents:
            await service("wallet", self.db).unfreeze(user_id, row.wallet_cents, key="unfreeze:" + row.id)
        await cas(self.db, row, values={"status": "cancelled"})

    async def payment_for_order(self, user_id: str, order_id: str):
        row = await self.db.scalar(select(Payment).where(Payment.user_id == user_id,
            Payment.order_id == order_id).with_for_update().execution_options(populate_existing=True))
        if row is None or row.status not in {"succeeded", "partially_refunded"}:
            raise MallError("payment_not_refundable")
        return view(row, PAYMENT_FIELDS)

    async def apply_refund(self, user_id: str, request: RefundInstruction):
        if request.wallet_cents and not enabled("wallet"):
            raise MallError("capability_unavailable", status=503)
        row = await owned(self.db, Payment, owner_id=user_id, resource_id=request.payment_id, lock=True)
        refunded = row.refunded_cents + request.amount_cents
        if refunded > row.amount_cents:
            raise MallError("refund_exceeds_payment")
        provider_ref = ""
        if request.external_cents:
            remote = await self.gateway.refund(self.db, request)
            provider_ref = remote.id
        if enabled("wallet"):
            await service("wallet", self.db).refund(user_id, wallet=request.wallet_cents,
                external=request.external_cents, key="refund:" + request.id)
        status = "refunded" if refunded == row.amount_cents else "partially_refunded"
        await cas(self.db, row, values={"refunded_cents": refunded, "status": status})
        return RefundReceipt(provider_ref=provider_ref, status="settled")
