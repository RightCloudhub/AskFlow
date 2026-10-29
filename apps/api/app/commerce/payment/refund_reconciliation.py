"""Refund statement comparison uses order-owned receipts through a service interface."""

from sqlalchemy import select

from app.commerce.order.refunds import RefundService
from app.commerce.payment.models import GatewayTransaction, Payment


async def differences(db):
    payments = await db.stream_scalars(select(Payment).where(Payment.refunded_cents > 0))
    async for payment in payments:
        receipts = await RefundService(db).payment_receipts(payment.id)
        provider = list(await db.scalars(select(GatewayTransaction).where(
            GatewayTransaction.payment_id == payment.id, GatewayTransaction.kind.in_(["refund", "late_refund"]))))
        for difference in compare(payment, receipts=receipts, provider=provider):
            yield difference


def compare(payment, *, receipts, provider):
    expected_total = payment.external_cents if payment.status == "late_refunded" else sum(
        row["amount_cents"] for row in receipts)
    if expected_total != payment.refunded_cents:
        yield difference(payment.id, kind="refund_snapshot", expected=expected_total, actual=payment.refunded_cents)
    expected = {row["provider_ref"]: row["external_cents"] for row in receipts if row["external_cents"]}
    if payment.status == "late_refunded":
        late = [row for row in provider if row.kind == "late_refund"]
        if len(late) != 1:
            yield difference(payment.id, kind="late_refund_receipts", expected=1, actual=len(late))
        expected.update({row.id: payment.external_cents for row in late})
    actual = {row.id: row.amount_cents for row in provider if row.status == "succeeded"}
    for reference in expected.keys() | actual.keys():
        if expected.get(reference) != actual.get(reference):
            yield difference(reference or payment.id, kind="refund_statement",
                             expected=expected.get(reference), actual=actual.get(reference))


def difference(entity, *, kind, expected, actual):
    return {"entity": entity, "kind": kind, "expected": {"value": expected}, "actual": {"value": actual}}
