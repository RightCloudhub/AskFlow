"""Explicit status graph; fulfillment remains independent after partial refunds."""

from app.commerce.core.errors import MallError
from app.commerce.core.events import publish
from app.commerce.core.repository import cas
from app.commerce.order.models import OrderHistory

FULFILLMENT = {"PENDING_PAYMENT", "PAID", "SHIPPED", "DELIVERED", "COMPLETED", "CANCELLED"}
FULFILLMENT_NEXT = {"PAID": "SHIPPED", "SHIPPED": "DELIVERED", "DELIVERED": "COMPLETED"}
TRANSITIONS = {
    "PENDING_PAYMENT": {"PAID", "CANCELLED"},
    "PAID": {"SHIPPED", "REFUNDING"},
    "SHIPPED": {"DELIVERED", "REFUNDING"},
    "DELIVERED": {"COMPLETED", "REFUNDING"},
    "COMPLETED": {"REFUNDING"},
    "REFUNDING": {"REFUNDED", "PARTIALLY_REFUNDED", "PAID", "SHIPPED", "DELIVERED", "COMPLETED"},
    "PARTIALLY_REFUNDED": {"REFUNDING", "SHIPPED", "DELIVERED", "COMPLETED"},
    "CANCELLED": set(), "REFUNDED": set(),
}


def allowed(before: str, after: str):
    if after not in TRANSITIONS.get(before, set()):
        raise MallError("invalid_order_transition")


async def transition(db, row, *, target: str, actor_id: str | None, reason: str = ""):
    allowed(row.status, target)
    if row.status == "PARTIALLY_REFUNDED" and target in FULFILLMENT:
        if FULFILLMENT_NEXT.get(row.fulfillment_status) != target:
            raise MallError("invalid_order_transition")
    before = row.status
    values = {"status": target}
    if target in FULFILLMENT:
        values["fulfillment_status"] = target
    await cas(db, row, values=values)
    db.add(OrderHistory(order_id=row.id, from_status=before, to_status=target,
                        actor_id=actor_id, reason=reason, version=row.version))
    await publish(db, row, event_type="mall.order." + target.lower(),
                  payload={"user_id": row.user_id, "order_id": row.id, "status": target,
                           "total_cents": row.total_cents, "currency": row.currency})
