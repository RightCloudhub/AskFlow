"""Inventory-owned aggregate measurements for operational projections."""

from sqlalchemy import case, func, or_, select

from app.commerce.infra.metrics import NEGATIVE_STOCK, OVERSOLD
from app.commerce.inventory.models import FlashRequest, FlashSaleSku, Inventory


async def snapshot(db):
    negative = await db.scalar(select(func.count()).select_from(Inventory).where(
        or_(Inventory.available < 0, Inventory.reserved < 0, Inventory.sold < 0)))
    queued = await db.scalar(select(func.count()).select_from(FlashRequest).where(FlashRequest.status == "queued"))
    stock_deficit = await db.scalar(select(func.coalesce(func.sum(
        case((Inventory.available < 0, -Inventory.available), else_=0)
        + case((Inventory.reserved < 0, -Inventory.reserved), else_=0)), 0)))
    flash_deficit = await db.scalar(select(func.coalesce(func.sum(
        case((FlashSaleSku.stock < 0, -FlashSaleSku.stock), else_=0)), 0)))
    oversold = stock_deficit + flash_deficit
    NEGATIVE_STOCK.set(negative)
    OVERSOLD.set(oversold)
    return {"negative_inventory": negative, "flash_queue": queued, "oversold_units": oversold}
