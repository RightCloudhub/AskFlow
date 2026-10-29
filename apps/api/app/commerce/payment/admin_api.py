"""Payment operations and provider reconciliation export."""

from datetime import date

from fastapi import APIRouter
from sqlalchemy import select

from app.commerce.admin.permissions import require
from app.commerce.core.constants import PAGE_SIZE
from app.commerce.core.schemas import view
from app.commerce.payment.models import GatewayTransaction, Payment
from app.commerce.payment.service import PAYMENT_FIELDS

FINANCE_RECONCILE = require("finance:reconcile")

router = APIRouter()


@router.get("")
async def payments(cursor: str = "", ctx=FINANCE_RECONCILE):
    rows = list(await ctx.db.scalars(select(Payment).where(Payment.id > cursor).order_by(Payment.id).limit(PAGE_SIZE)))
    return {"items": [view(row, PAYMENT_FIELDS) for row in rows],
            "next_cursor": rows[-1].id if len(rows) == PAGE_SIZE else None}


@router.get("/statement/{day}")
async def statement(day: date, cursor: str = "", ctx=FINANCE_RECONCILE):
    from datetime import UTC, datetime, time, timedelta

    start = datetime.combine(day, time.min, UTC)
    rows = list(await ctx.db.scalars(select(GatewayTransaction).where(
        GatewayTransaction.id > cursor, GatewayTransaction.settled_at >= start,
        GatewayTransaction.settled_at < start + timedelta(days=1))
        .order_by(GatewayTransaction.id).limit(PAGE_SIZE)))
    fields = ("id", "payment_id", "refund_id", "kind", "amount_cents", "currency", "status")
    return {"items": [view(row, fields) for row in rows], "data_source": "mock",
            "next_cursor": rows[-1].id if len(rows) == PAGE_SIZE else None}
