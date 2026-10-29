"""Rebuild disposable Redis admission counters from committed offers and requests."""

from sqlalchemy import func, select

from app.commerce.infra.runtime import infra
from app.commerce.inventory.models import FlashRequest, FlashSale, FlashSaleSku
from app.core.config import get_settings


async def reconcile(db):
    if get_settings().flash_sale_backend != "redis":
        return
    offers = await db.scalars(select(FlashSaleSku).join(FlashSale,
        FlashSale.id == FlashSaleSku.sale_id).where(FlashSale.status == "active"))
    for offer in offers:
        queued = await db.scalar(select(func.count()).select_from(FlashRequest).where(
            FlashRequest.sale_id == offer.sale_id, FlashRequest.sku_id == offer.sku_id,
            FlashRequest.status == "queued"))
        # This is admission only. Races may over-admit; database stock CAS still rejects excess.
        await infra().redis.client().set("mall:flash:" + offer.id, max(0, offer.stock - queued))
