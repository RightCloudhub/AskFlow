"""Oversell protection is checked against independent transactions/connections."""

import asyncio

import pytest
from sqlalchemy import func, select

from app.commerce.core.errors import MallError
from app.commerce.inventory.models import Inventory, InventoryReservation
from app.commerce.order.models import Order
from .helpers import place, seed, transaction


@pytest.mark.asyncio
async def test_thousand_buyers_for_one_hundred_items(mall_runtime):
    identity = await seed(mall_runtime, stock=100)

    async def buyer():
        try:
            await transaction(mall_runtime, lambda db: place(db, identity))
            return True
        except MallError as exc:
            assert exc.code == "inventory_insufficient"
            return False

    results = await asyncio.gather(*(buyer() for _ in range(1000)))
    assert sum(results) == 100
    async with mall_runtime.sessions() as db:
        stock = await db.scalar(select(Inventory).where(Inventory.sku_id == identity["sku_id"]))
        assert (stock.available, stock.reserved) == (0, 100)
        assert await db.scalar(select(func.count()).select_from(Order)) == 100
        assert await db.scalar(select(func.count()).select_from(InventoryReservation)) == 100
