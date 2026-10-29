"""Conditional inventory mutations are the source of truth on SQLite and PG."""

from sqlalchemy import select, update

from app.commerce.core.errors import MallError
from app.commerce.core.repository import cas, insert_once
from app.commerce.core.schemas import view
from app.commerce.inventory.models import Inventory, InventoryMovement, InventoryReservation

STOCK_FIELDS = ("sku_id", "available", "reserved", "sold", "version")


class InventoryService:
    def __init__(self, db):
        self.db = db

    async def get(self, sku_id: str):
        row = await self.db.scalar(select(Inventory).where(Inventory.sku_id == sku_id))
        if row is None:
            raise MallError("resource_not_found", status=404)
        return view(row, STOCK_FIELDS)

    async def reserve(self, order_id: str, items, *, expires_at):
        for item in sorted(items, key=lambda value: value["sku_id"]):
            await self._reserve_one(order_id, item, expires_at=expires_at)

    async def _reserve_one(self, order_id: str, item, *, expires_at):
        qty, sku_id = item["qty"], item["sku_id"]
        if type(qty) is not int or qty <= 0:
            raise MallError("invalid_quantity", status=422)
        result = await self.db.execute(update(Inventory).where(Inventory.sku_id == sku_id,
            Inventory.available >= qty).values(available=Inventory.available - qty,
            reserved=Inventory.reserved + qty, version=Inventory.version + 1))
        if result.rowcount != 1:
            raise MallError("inventory_insufficient")
        self.db.add(InventoryReservation(order_id=order_id, sku_id=sku_id, qty=qty,
                                          expires_at=expires_at))
        self.db.add(InventoryMovement(sku_id=sku_id, order_id=order_id,
            business_key="reserve:" + order_id + ":" + sku_id,
            available_delta=-qty, reserved_delta=qty, kind="reserve"))
        await self.db.flush()

    async def finish(self, order_id: str, *, consume: bool):
        rows = await self.db.scalars(select(InventoryReservation).where(
            InventoryReservation.order_id == order_id).order_by(InventoryReservation.sku_id)
            .with_for_update().execution_options(populate_existing=True))
        for row in rows:
            if row.status != "reserved":
                continue
            await self._finish_one(row, consume=consume)

    async def _finish_one(self, row, *, consume: bool):
        status = "consumed" if consume else "released"
        await cas(self.db, row, values={"status": status})
        values = {"reserved": Inventory.reserved - row.qty, "version": Inventory.version + 1}
        values["sold" if consume else "available"] = (
            Inventory.sold if consume else Inventory.available) + row.qty
        result = await self.db.execute(update(Inventory).where(Inventory.sku_id == row.sku_id,
            Inventory.reserved >= row.qty).values(**values))
        if result.rowcount != 1:
            raise MallError("inventory_invariant_failed")
        self.db.add(InventoryMovement(sku_id=row.sku_id, order_id=row.order_id,
            business_key=status + ":" + row.order_id + ":" + row.sku_id,
            available_delta=0 if consume else row.qty, reserved_delta=-row.qty, kind=status))

    async def replenish(self, sku_id: str, payload, *, business_key: str):
        from app.commerce.catalog.service import CatalogService

        await CatalogService(self.db).ensure_sku(sku_id)
        await insert_once(self.db, Inventory, values={"sku_id": sku_id}, unique=["sku_id"])
        row = await self.db.scalar(select(Inventory).where(Inventory.sku_id == sku_id)
                                   .with_for_update().execution_options(populate_existing=True))
        if row.version != payload.expected_version:
            raise MallError("version_conflict")
        await cas(self.db, row, values={"available": row.available + payload.quantity})
        self.db.add(InventoryMovement(sku_id=sku_id, business_key=business_key,
            available_delta=payload.quantity, reserved_delta=0, kind="replenish"))
        return view(row, STOCK_FIELDS)
