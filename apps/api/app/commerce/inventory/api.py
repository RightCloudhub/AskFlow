"""Public stock availability; allocation remains server-authoritative."""

from fastapi import APIRouter

from app.commerce.core.deps import MallDb
from app.commerce.inventory.service import InventoryService

router = APIRouter()

from app.commerce.inventory.flash_api import router as flash_router

router.include_router(flash_router)


@router.get("/{sku_id}")
async def stock(sku_id: str, db: MallDb):
    return await InventoryService(db).get(sku_id)
