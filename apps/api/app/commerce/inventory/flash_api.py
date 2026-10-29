"""Burst entry returns a durable request ID; only database settlement creates an order."""

from fastapi import APIRouter
from sqlalchemy import select

from app.commerce.core.commands import command
from app.commerce.core.deps import MallContext, MallDb
from app.commerce.core.repository import owned
from app.commerce.core.schemas import Schema, view
from app.commerce.inventory.flash import enqueue
from app.commerce.inventory.models import FlashRequest, FlashSale
from app.services.agent.gateway.idempotency import args_hash

router = APIRouter()


class Request(Schema):
    sku_id: str


@router.get("/flash-sales")
async def sales(db: MallDb):
    rows = await db.scalars(select(FlashSale).where(FlashSale.status == "active"))
    return {"items": [view(row, ("id", "name", "starts_at", "ends_at")) for row in rows]}


@router.post("/flash-sales/{sale_id}")
async def request(sale_id: str, payload: Request, ctx: MallContext):
    key = args_hash({"user_id": ctx.user.id, "key": ctx.key})
    return await command(ctx, "flash.request:" + sale_id, payload=payload,
                         action=lambda: enqueue(ctx, sale_id, sku_id=payload.sku_id, request_key=key))


@router.get("/flash-requests/{request_id}")
async def progress(request_id: str, ctx: MallContext):
    row = await owned(ctx.db, FlashRequest, owner_id=ctx.user.id, resource_id=request_id)
    return view(row, ("id", "status", "order_id", "error_code"))
