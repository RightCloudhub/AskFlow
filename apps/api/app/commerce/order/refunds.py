"""Refund quota is reserved at application time and released only on a known outcome."""

from sqlalchemy import select

from app.commerce.admin.settings_service import value
from app.commerce.core.errors import MallError
from app.commerce.core.events import publish
from app.commerce.core.repository import cas, owned, owned_page
from app.commerce.core.schemas import view
from app.commerce.core.services import service
from app.commerce.order.refund_models import Refund
from app.commerce.order.service import OrderService
from app.commerce.order.states import transition
from app.commerce.payment.contracts import RefundInstruction

REFUND_FIELDS = ("id", "order_id", "amount_cents", "wallet_cents", "external_cents", "status",
                 "reason", "destination", "provider_ref", "version", "created_at")
REFUNDABLE = {"PAID", "SHIPPED", "DELIVERED", "COMPLETED", "PARTIALLY_REFUNDED"}


class RefundService:
    def __init__(self, db):
        self.db = db

    async def get(self, user_id: str, refund_id: str):
        row = await owned(self.db, Refund, owner_id=user_id, resource_id=refund_id)
        return view(row, REFUND_FIELDS)

    async def list(self, user_id: str, *, cursor: str = ""):
        rows, after = await owned_page(self.db, Refund, owner_id=user_id, cursor=cursor)
        return {"items": [view(row, REFUND_FIELDS) for row in rows], "next_cursor": after}

    async def order_status(self, user_id: str, order_id: str):
        await OrderService(self.db).get(user_id, order_id)
        row = await self.db.scalar(select(Refund).where(Refund.user_id == user_id,
            Refund.order_id == order_id).order_by(Refund.created_at.desc(), Refund.id.desc()).limit(1))
        return view(row, REFUND_FIELDS) if row else None

    async def payment_receipts(self, payment_id: str):
        """Internal reconciliation projection; callers already hold finance authority."""
        rows = await self.db.scalars(select(Refund).where(Refund.payment_id == payment_id,
                                                        Refund.status == "settled"))
        fields = ("id", "amount_cents", "external_cents", "provider_ref")
        return [view(row, fields) for row in rows]

    async def request(self, user_id: str, *, order_id: str, payload, key: str, force_review: bool = False):
        order = await OrderService(self.db).row(user_id, order_id, lock=True)
        if order.status not in REFUNDABLE:
            raise MallError("order_not_refundable")
        if payload.amount_cents > order.total_cents - order.refunded_cents - order.refund_reserved_cents:
            raise MallError("refund_exceeds_payment")
        payment = await service("payment", self.db).payment_for_order(user_id, order_id)
        wallet, external = await self._split(payment, payload)
        automatic = not force_review and payload.amount_cents <= await value(self.db, "mall_auto_refund_cents")
        row = Refund(order_id=order_id, user_id=user_id, payment_id=payment["id"],
            amount_cents=payload.amount_cents, wallet_cents=wallet, external_cents=external,
            request_key=key, reason=payload.reason, destination=payload.destination,
            original_status=order.status, status="approved" if automatic else "requested")
        self.db.add(row)
        await cas(self.db, order, values={"refund_reserved_cents": order.refund_reserved_cents + payload.amount_cents})
        await transition(self.db, order, target="REFUNDING", actor_id=user_id)
        await self.db.flush()
        await publish(self.db, row, event_type="mall.refund.requested", payload={
            "user_id": user_id, "order_id": order_id, "refund_id": row.id})
        return view(row, REFUND_FIELDS)

    async def _split(self, payment, payload):
        rows = await self.db.scalars(select(Refund).where(Refund.payment_id == payment["id"],
                                                         Refund.status.not_in(["rejected", "failed"])))
        used_wallet = sum(row.wallet_cents for row in rows if row.destination == "original")
        wallet = min(payload.amount_cents, max(0, payment["wallet_cents"] - used_wallet))
        if payload.destination == "wallet":
            wallet = payload.amount_cents
        return wallet, payload.amount_cents - wallet

    async def review(self, refund_id: str, *, approved: bool, actor_id: str, expected_version: int):
        row = await self.db.get(Refund, refund_id)
        if row is None:
            raise MallError("resource_not_found", status=404)
        order = await OrderService(self.db).row(row.user_id, row.order_id, lock=True)
        await self.db.refresh(row)
        if row.status != "requested" or row.version != expected_version:
            raise MallError("refund_review_conflict")
        await cas(self.db, row, values={"status": "approved" if approved else "rejected",
                                       "approval_actor": actor_id})
        if not approved:
            await cas(self.db, order, values={"refund_reserved_cents": order.refund_reserved_cents - row.amount_cents})
            await transition(self.db, order, target=row.original_status, actor_id=actor_id)
        return view(row, REFUND_FIELDS)

    async def process(self, refund_id: str):
        row = await self.db.get(Refund, refund_id)
        if row is None:
            return
        order = await OrderService(self.db).row(row.user_id, row.order_id, lock=True)
        await self.db.refresh(row)
        if row.status != "approved":
            return
        receipt = await service("payment", self.db).apply_refund(row.user_id, RefundInstruction(
            id=row.id, payment_id=row.payment_id, amount_cents=row.amount_cents,
            wallet_cents=row.wallet_cents, external_cents=row.external_cents))
        total = order.refunded_cents + row.amount_cents
        await cas(self.db, order, values={"refunded_cents": total,
            "refund_reserved_cents": order.refund_reserved_cents - row.amount_cents})
        await cas(self.db, row, values={"status": receipt.status, "provider_ref": receipt.provider_ref})
        target = "REFUNDED" if total == order.total_cents else "PARTIALLY_REFUNDED"
        await transition(self.db, order, target=target, actor_id=row.user_id)
        await publish(self.db, row, event_type="mall.refund.settled", payload={
            "user_id": row.user_id, "refund_id": row.id, "order_id": row.order_id})
        return view(row, REFUND_FIELDS)
