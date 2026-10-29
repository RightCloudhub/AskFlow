"""A provider success never resurrects a cancelled or expired order."""

from datetime import UTC, datetime

from app.commerce.core.events import publish
from app.commerce.core.repository import cas
from app.commerce.core.services import enabled, service

FINAL = {"succeeded", "partially_refunded", "refunded", "late_payment", "late_refunded"}


async def settle(db, row, *, status: str):
    if row.status in FINAL:
        return
    if status == "failed":
        await _failed(db, row)
        return
    if row.topup_id:
        from app.commerce.wallet.topups import complete

        await complete(db, row.user_id, topup_id=row.topup_id, payment_id=row.id)
    else:
        order = await service("order", db).get(row.user_id, row.order_id, lock=True)
        expired = datetime.fromisoformat(order["expires_at"]) <= datetime.now(UTC)
        if order["status"] != "PENDING_PAYMENT" or expired or row.status != "pending":
            await _late(db, row)
            return
        if enabled("wallet"):
            await service("wallet", db).settle(row.user_id, wallet=row.wallet_cents,
                external=row.external_cents, key="payment:" + row.id)
        await service("order", db).paid(row.user_id, row.order_id, wallet_cents=row.wallet_cents)
    await cas(db, row, values={"status": "succeeded"})
    await publish(db, row, event_type="mall.payment.succeeded", payload={"user_id": row.user_id,
        "payment_id": row.id, "order_id": row.order_id, "amount_cents": row.amount_cents})


async def _failed(db, row):
    if row.status != "pending":
        return
    if row.wallet_cents:
        await service("wallet", db).unfreeze(row.user_id, row.wallet_cents, key="unfreeze:" + row.id)
    await cas(db, row, values={"status": "failed"})
    await publish(db, row, event_type="mall.payment.failed", payload={"user_id": row.user_id, "payment_id": row.id})


async def _late(db, row):
    if row.status == "pending" and row.wallet_cents:
        await service("wallet", db).unfreeze(row.user_id, row.wallet_cents, key="unfreeze:" + row.id)
    if enabled("wallet"):
        await service("wallet", db).transfer(row.user_id, amount=row.external_cents,
            key="late:" + row.id, debit="gateway", credit="refund_clearing")
    await cas(db, row, values={"status": "late_payment"})
    await publish(db, row, event_type="mall.payment.late", payload={"user_id": row.user_id,
        "payment_id": row.id, "requires_review": True})
