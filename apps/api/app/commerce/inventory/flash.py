"""Redis burst admission plus a durable database queue and conditional allocation."""

from datetime import UTC, datetime, timedelta
from http import HTTPStatus

from sqlalchemy import select, update

from app.commerce.core.errors import MallError
from app.commerce.core.repository import cas
from app.commerce.core.schemas import utc
from app.commerce.core.services import service
from app.commerce.infra.runtime import infra
from app.commerce.inventory.models import FlashRequest, FlashSale, FlashSaleSku
from app.core.config import get_settings

ADMISSION_KEY_COUNT = 3
ADMIT = """
if redis.call('exists', KEYS[2]) == 1 then return 1 end
local stock = tonumber(redis.call('get', KEYS[1]) or '-1')
if stock < 1 then return 0 end
redis.call('decr', KEYS[1])
redis.call('set', KEYS[2], ARGV[1], 'EX', ARGV[2])
redis.call('xadd', KEYS[3], '*', 'request_id', ARGV[1])
return 1
"""
STREAM = "mall:flash:requests"


async def enqueue(ctx, sale_id: str, *, sku_id: str, request_key: str):
    sale = await ctx.db.get(FlashSale, sale_id)
    now = datetime.now(UTC)
    if sale is None or sale.status != "active" or not utc(sale.starts_at) <= now < utc(sale.ends_at):
        raise MallError("flash_sale_closed")
    offer = await ctx.db.scalar(select(FlashSaleSku).where(FlashSaleSku.sale_id == sale_id, FlashSaleSku.sku_id == sku_id))
    if offer is None:
        raise MallError("resource_not_found", status=HTTPStatus.NOT_FOUND)
    existing = await ctx.db.scalar(select(FlashRequest).where(FlashRequest.user_id == ctx.user.id,
        FlashRequest.sale_id == sale_id, FlashRequest.sku_id == sku_id))
    if existing:
        return {"id": existing.id, "status": existing.status, "order_id": existing.order_id}
    row = FlashRequest(user_id=ctx.user.id, sale_id=sale_id, sku_id=sku_id, request_key=request_key,
        expires_at=now + timedelta(seconds=get_settings().mall_reservation_seconds))
    ctx.db.add(row)
    await ctx.db.flush()
    if get_settings().flash_sale_backend == "redis":
        client = infra().redis.client()
        key = "mall:flash:" + offer.id
        admitted = await client.eval(ADMIT, ADMISSION_KEY_COUNT, key, key + ":user:" + ctx.user.id, STREAM,
                                     row.id, get_settings().mall_reservation_seconds)
        if not admitted:
            raise MallError("inventory_insufficient")
    else:
        await fulfill(ctx.db, row)
    return {"id": row.id, "status": row.status, "order_id": row.order_id}


async def fulfill(db, row):
    if row.status != "queued":
        return
    if utc(row.expires_at) <= datetime.now(UTC):
        raise MallError("flash_request_expired")
    offer = await db.scalar(select(FlashSaleSku).where(FlashSaleSku.sale_id == row.sale_id,
        FlashSaleSku.sku_id == row.sku_id).with_for_update().execution_options(populate_existing=True))
    result = await db.execute(update(FlashSaleSku).where(FlashSaleSku.id == offer.id,
        FlashSaleSku.stock > 0).values(stock=FlashSaleSku.stock - 1, version=FlashSaleSku.version + 1))
    if result.rowcount != 1:
        raise MallError("inventory_insufficient")
    order = await service("order", db).flash_order(row.user_id, sku_id=row.sku_id, price_cents=offer.price_cents)
    await cas(db, row, values={"status": "ordered", "order_id": order["id"]})
