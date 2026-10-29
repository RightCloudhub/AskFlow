"""Create bounded sale offers; Redis counters are a disposable admission hint."""

from datetime import datetime

from fastapi import APIRouter
from pydantic import Field

from app.commerce.admin.permissions import require
from app.commerce.core.commands import command
from app.commerce.core.constants import NAME_SIZE
from app.commerce.core.errors import MallError
from app.commerce.core.schemas import PositiveCents, Schema, utc
from app.commerce.core.services import service
from app.commerce.infra.runtime import infra
from app.commerce.inventory.models import FlashSale, FlashSaleSku
from app.core.config import get_settings

MAX_FLASH_STOCK = 1000000
router = APIRouter()


class Sale(Schema):
    name: str = Field(min_length=1, max_length=NAME_SIZE)
    starts_at: datetime
    ends_at: datetime
    sku_id: str
    stock: int = Field(gt=0, le=MAX_FLASH_STOCK, strict=True)
    price_cents: PositiveCents


@router.post("/flash-sales")
async def create(payload: Sale, ctx=require("inventory:write")):
    async def perform():
        if utc(payload.ends_at) <= utc(payload.starts_at):
            raise MallError("sale_dates_invalid", status=422)
        await service("catalog", ctx.db).quote(payload.sku_id)
        sale = FlashSale(name=payload.name, starts_at=utc(payload.starts_at), ends_at=utc(payload.ends_at))
        ctx.db.add(sale)
        await ctx.db.flush()
        offer = FlashSaleSku(sale_id=sale.id, sku_id=payload.sku_id, stock=payload.stock,
                            price_cents=payload.price_cents, per_user_limit=1)
        ctx.db.add(offer)
        await ctx.db.flush()
        if get_settings().flash_sale_backend == "redis":
            await infra().redis.client().set("mall:flash:" + offer.id, payload.stock, nx=True)
        return {"id": sale.id, "sku_id": offer.sku_id, "stock": offer.stock}

    return await command(ctx, "flash.create", payload=payload, action=perform)
