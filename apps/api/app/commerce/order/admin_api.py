"""Operational order transitions and refund approvals."""

from fastapi import APIRouter
from sqlalchemy import select

from app.commerce.admin.permissions import require
from app.commerce.core.commands import command
from app.commerce.core.constants import PAGE_SIZE
from app.commerce.core.errors import MallError
from app.commerce.core.schemas import Versioned, view
from app.commerce.order.models import Order
from app.commerce.order.refund_models import Refund
from app.commerce.order.refunds import REFUND_FIELDS, RefundService
from app.commerce.order.schemas import Transition
from app.commerce.order.service import ORDER_FIELDS, OrderService

router = APIRouter()


class Review(Versioned):
    approved: bool


@router.get("")
async def orders(cursor: str = "", ctx=require("order:read")):
    rows = list(await ctx.db.scalars(select(Order).where(Order.id > cursor).order_by(Order.id).limit(PAGE_SIZE)))
    return {"items": [view(row, ORDER_FIELDS) for row in rows],
            "next_cursor": rows[-1].id if len(rows) == PAGE_SIZE else None}


@router.post("/{order_id}/transition")
async def advance(order_id: str, payload: Transition, ctx=require("order:write")):
    row = await ctx.db.get(Order, order_id)
    if row is None:
        raise MallError("resource_not_found", status=404)
    return await command(ctx, "order.transition:" + order_id, payload=payload,
        action=lambda: OrderService(ctx.db).advance(row.user_id, row.id, payload=payload, actor_id=ctx.user.id))


@router.get("/refunds/pending")
async def refunds(cursor: str = "", ctx=require("order:refund")):
    rows = list(await ctx.db.scalars(select(Refund).where(Refund.id > cursor)
                                    .order_by(Refund.id).limit(PAGE_SIZE)))
    return {"items": [view(row, REFUND_FIELDS) for row in rows],
            "next_cursor": rows[-1].id if len(rows) == PAGE_SIZE else None}


@router.post("/refunds/{refund_id}/review")
async def review(refund_id: str, payload: Review, ctx=require("order:refund")):
    return await command(ctx, "refund.review:" + refund_id, payload=payload,
        action=lambda: RefundService(ctx.db).review(refund_id, approved=payload.approved,
            actor_id=ctx.user.id, expected_version=payload.expected_version))
