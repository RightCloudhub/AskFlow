"""Inventory-owned aggregate measurements for operational projections."""

from sqlalchemy import func, or_, select

from app.commerce.inventory.models import FlashRequest, Inventory


async def snapshot(db):
    negative = await db.scalar(select(func.count()).select_from(Inventory).where(
        or_(Inventory.available < 0, Inventory.reserved < 0, Inventory.sold < 0)))
    queued = await db.scalar(select(func.count()).select_from(FlashRequest).where(FlashRequest.status == "queued"))
    return {"negative_inventory": negative, "flash_queue": queued}
