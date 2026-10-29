"""Late mock receipts are refunded once without reopening cancelled orders."""

from app.commerce.core.events import publish
from app.commerce.core.repository import cas, owned
from app.commerce.core.services import enabled, service
from app.commerce.payment.gateway import MockGateway
from app.commerce.payment.models import Payment
from app.commerce.payment.settlement import settle


async def compensate(db, payment_id: str):
    candidate = await db.get(Payment, payment_id)
    if candidate is None:
        return
    if candidate.order_id:
        await service("order", db).get(candidate.user_id, candidate.order_id, lock=True)
    row = await owned(db, Payment, owner_id=candidate.user_id, resource_id=payment_id, lock=True)
    if row.status == "late_payment":
        await refund_late(db, row)
        return
    if row.status not in {"pending", "cancelled", "failed"}:
        return
    remote = await MockGateway().query(db, row.request_key)
    if remote.status in {"succeeded", "failed"}:
        row.payer_hash = remote.payer_hash
        await settle(db, row, status=remote.status)


async def refund_late(db, row):
    remote = await MockGateway().refund_late(db, row)
    if enabled("wallet"):
        await service("wallet", db).transfer(row.user_id, amount=row.external_cents,
            key="late-refund:" + row.id, debit="refund_clearing", credit="gateway")
    await cas(db, row, values={"status": "late_refunded", "refunded_cents": row.external_cents})
    await publish(db, row, event_type="mall.payment.late_refunded", payload={
        "user_id": row.user_id, "payment_id": row.id, "provider_ref": remote.id})
