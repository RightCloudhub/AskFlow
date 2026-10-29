"""Authoritative visibility/pricing; order writers lock current catalog rows."""

from datetime import UTC, datetime

from sqlalchemy import or_, select

from app.commerce.catalog.models import Category, Sku, SkuPrice, Spu
from app.commerce.core.errors import MallError
from app.commerce.core.events import publish
from app.commerce.core.repository import cas
from app.commerce.core.schemas import view
from app.core.config import get_settings

SKU_FIELDS = ("id", "spu_id", "code", "title", "attributes", "status", "currency", "version")
SPU_FIELDS = ("id", "title", "description", "category_id", "attributes", "images", "status", "version")


class CatalogService:
    def __init__(self, db):
        self.db = db

    async def entity(self, model, resource_id: str, *, lock: bool = False):
        statement = select(model).where(model.id == resource_id)
        if lock:
            statement = statement.with_for_update()
        row = await self.db.scalar(statement.execution_options(populate_existing=True))
        if row is None:
            raise MallError("resource_not_found", status=404)
        return row

    async def quote(self, sku_id: str, *, lock: bool = False):
        sku = await self.entity(Sku, sku_id, lock=lock)
        spu = await self.entity(Spu, sku.spu_id, lock=lock)
        if sku.status != "active" or spu.status != "active":
            raise MallError("product_unavailable")
        price = await self.current_price(sku.id)
        return {**view(sku, SKU_FIELDS), "price_cents": price.activity_cents
                if price.activity_cents is not None else price.sale_cents,
                "original_cents": price.original_cents}

    async def ensure_sku(self, sku_id: str):
        row = await self.entity(Sku, sku_id)
        return view(row, SKU_FIELDS)

    async def current_price(self, sku_id: str):
        now = datetime.now(UTC)
        row = await self.db.scalar(select(SkuPrice).where(SkuPrice.sku_id == sku_id,
            SkuPrice.valid_from <= now, or_(SkuPrice.valid_to.is_(None), SkuPrice.valid_to > now))
            .order_by(SkuPrice.valid_from.desc(), SkuPrice.id.desc()).limit(1))
        if row is None:
            raise MallError("price_unavailable")
        return row

    async def detail(self, spu_id: str):
        spu = await self.entity(Spu, spu_id)
        if spu.status != "active":
            raise MallError("resource_not_found", status=404)
        ids = await self.db.scalars(select(Sku.id).where(Sku.spu_id == spu_id, Sku.status == "active"))
        data = view(spu, SPU_FIELDS)
        data["images"] = ["/api/v1/mall/files/" + key for key in spu.images]
        return {**data, "skus": [await self.quote(key) for key in ids]}

    async def update_product(self, product_id: str, payload):
        row = await self.entity(Spu, product_id, lock=True)
        if row.version != payload.expected_version:
            raise MallError("version_conflict")
        if payload.category_id:
            await self.entity(Category, payload.category_id)
        before = view(row, SPU_FIELDS)
        await cas(self.db, row, values=payload.model_dump(exclude={"expected_version"}))
        await self.changed(row, product_id)
        return {**view(row, SPU_FIELDS), "before": before}

    async def create_category(self, payload):
        if payload.parent_id:
            await self.entity(Category, payload.parent_id)
        row = Category(**payload.model_dump())
        self.db.add(row)
        await self.db.flush()
        return view(row, ("id", "name", "slug", "parent_id", "version"))

    async def create_product(self, payload):
        if payload.category_id:
            await self.entity(Category, payload.category_id)
        row = Spu(**payload.model_dump())
        self.db.add(row)
        await self.db.flush()
        return view(row, SPU_FIELDS)

    async def create_sku(self, payload):
        await self.entity(Spu, payload.spu_id, lock=True)
        row = Sku(**payload.model_dump(exclude={"sale_cents", "original_cents"}),
                  currency=get_settings().mall_currency)
        self.db.add(row)
        await self.db.flush()
        self.db.add(SkuPrice(sku_id=row.id, sale_cents=payload.sale_cents,
                            original_cents=payload.original_cents, valid_from=datetime.now(UTC)))
        await self.db.flush()
        return view(row, SKU_FIELDS)

    async def visibility(self, resource_id: str, payload, *, sku: bool):
        row = await self.entity(Sku if sku else Spu, resource_id, lock=True)
        if row.version != payload.expected_version:
            raise MallError("version_conflict")
        before = row.status
        await cas(self.db, row, values={"status": payload.status})
        await self.changed(row, row.spu_id if sku else row.id)
        return {"id": row.id, "status": row.status, "version": row.version, "before": before}

    async def price(self, sku_id: str, payload):
        row = await self.entity(Sku, sku_id, lock=True)
        if row.version != payload.expected_version:
            raise MallError("version_conflict")
        prior = await self.current_price(sku_id)
        prior.valid_to = datetime.now(UTC)
        self.db.add(SkuPrice(sku_id=sku_id, valid_from=prior.valid_to,
                            **payload.model_dump(exclude={"expected_version"})))
        await cas(self.db, row, values={})
        await self.changed(row, row.spu_id)
        return {"id": sku_id, "version": row.version, "before_cents": prior.sale_cents}

    async def changed(self, row, spu_id: str):
        await publish(self.db, row, event_type="mall.catalog.changed", payload={"spu_id": spu_id})
