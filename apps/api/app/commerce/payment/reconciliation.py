"""Compare durable mock statements with local payment receipts, without repairing."""

from datetime import UTC, date, datetime, time, timedelta

from sqlalchemy import select

from app.commerce.payment.models import GatewayTransaction, Payment

PAID = frozenset({"succeeded", "partially_refunded", "refunded", "late_payment", "late_refunded"})


async def differences(db, *, business_date: str):
    from app.commerce.payment.refund_reconciliation import differences as refund_differences

    start = datetime.combine(date.fromisoformat(business_date), time.min, UTC)
    end = start + timedelta(days=1)
    rows = await db.stream_scalars(select(GatewayTransaction).where(
        GatewayTransaction.settled_at >= start, GatewayTransaction.settled_at < end))
    async for remote in rows:
        payment = await db.get(Payment, remote.payment_id) if remote.payment_id else None
        difference = compare(remote, payment)
        if difference:
            yield difference
    statement = select(Payment).where(Payment.external_cents > 0, Payment.status.in_(PAID),
        ~select(GatewayTransaction.id).where(GatewayTransaction.payment_id == Payment.id,
            GatewayTransaction.kind == "charge").exists())
    async for payment in await db.stream_scalars(statement):
        yield {"entity": payment.id, "kind": "gateway_missing",
               "expected": {"amount_cents": payment.external_cents}, "actual": {}}
    pending_provider = select(Payment).join(GatewayTransaction, GatewayTransaction.id == Payment.provider_ref).where(
        Payment.status.in_(PAID), GatewayTransaction.status != "succeeded")
    async for payment in await db.stream_scalars(pending_provider):
        yield {"entity": payment.id, "kind": "gateway_unsettled",
               "expected": {"status": "succeeded"}, "actual": {"status": "not_settled"}}
    async for difference in refund_differences(db):
        yield difference


def compare(remote, payment):
    actual = {"amount_cents": remote.amount_cents, "currency": remote.currency, "status": remote.status}
    if payment is None:
        return {"entity": remote.id, "kind": "payment_missing", "expected": {}, "actual": actual}
    if remote.kind != "charge":
        return refund_difference(remote, payment, actual=actual)
    expected = {"amount_cents": payment.external_cents, "currency": payment.currency,
                "status": "succeeded" if payment.status in PAID else payment.status}
    if actual != expected or payment.provider_ref != remote.id:
        return {"entity": payment.id, "kind": "gateway_receipt", "expected": expected, "actual": actual}
    return None


def refund_difference(remote, payment, *, actual):
    expected = {"currency": payment.currency, "status": "succeeded"}
    valid = remote.status == "succeeded" and remote.currency == payment.currency
    valid = valid and 0 < remote.amount_cents <= payment.refunded_cents
    if remote.kind == "late_refund":
        valid = valid and payment.status == "late_refunded" and remote.amount_cents == payment.external_cents
    if not valid:
        return {"entity": remote.id, "kind": "gateway_refund", "expected": expected, "actual": actual}
    return None
