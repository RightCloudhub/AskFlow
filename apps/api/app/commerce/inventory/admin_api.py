"""Stock operations require explicit versions and business keys."""

from fastapi import APIRouter
from pydantic import Field
from sqlalchemy import select

from app.commerce.admin.permissions import require
from app.commerce.core.commands import command
from app.commerce.core.constants import PAGE_SIZE
from app.commerce.core.schemas import Versioned, view
from app.commerce.inventory.models import Inventory
from app.commerce.inventory.service import InventoryService
from app.services.agent.gateway.idempotency import args_hash

MAX_STOCK_CHANGE = 1000000000
router = APIRouter()

from app.commerce.inventory.flash_admin import router as flash_router

router.include_router(flash_router)


class Replenish(Versioned):
    quantity: int = Field(strict=True, gt=0, le=MAX_STOCK_CHANGE)


@router.get("")
async def inventory(cursor: str = "", ctx=require("inventory:write")):
    rows = list(await ctx.db.scalars(select(Inventory).where(Inventory.id > cursor)
        .order_by(Inventory.id).limit(PAGE_SIZE + 1)))
    return {"items": [view(row, ("id", "sku_id", "available", "reserved", "version")) for row in rows[:PAGE_SIZE]],
            "next_cursor": rows[PAGE_SIZE - 1].id if len(rows) > PAGE_SIZE else None}


@router.get("/{sku_id}")
async def stock(sku_id: str, ctx=require("inventory:write")):
    return await InventoryService(ctx.db).get(sku_id)


@router.post("/{sku_id}/replenish")
async def replenish(sku_id: str, payload: Replenish, ctx=require("inventory:write")):
    key = args_hash({"user": ctx.user.id, "sku": sku_id, "key": ctx.key})
    return await command(ctx, "inventory.replenish:" + sku_id, payload=payload,
        action=lambda: InventoryService(ctx.db).replenish(sku_id, payload, business_key=key))
