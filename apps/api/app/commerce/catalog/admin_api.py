"""Audited catalog management; no client-selected prices at checkout."""

from hashlib import sha256

from fastapi import APIRouter, UploadFile
from sqlalchemy import select

from app.commerce.admin.permissions import require
from app.commerce.catalog import schemas
from app.commerce.catalog.models import Sku, Spu
from app.commerce.catalog.service import CatalogService, SPU_FIELDS, SKU_FIELDS
from app.commerce.core.commands import command
from app.commerce.core.constants import PAGE_SIZE
from app.commerce.core.errors import MallError
from app.commerce.core.schemas import view
from app.commerce.infra.runtime import infra
from app.core.config import get_settings

router = APIRouter()


@router.post("/images")
async def image(file: UploadFile, ctx=require("catalog:write")):
    data = await file.read(get_settings().max_upload_bytes + 1)
    if len(data) > get_settings().max_upload_bytes:
        raise MallError("upload_size_invalid", status=422)

    async def perform():
        return {"key": await infra().objects.put(data, content_type=file.content_type or "")}

    payload = {"digest": sha256(data).hexdigest(), "content_type": file.content_type}
    return await command(ctx, "catalog.image", payload=payload, action=perform)


@router.get("/skus")
async def skus(cursor: str = "", ctx=require("catalog:write")):
    rows = list(await ctx.db.scalars(select(Sku).where(Sku.id > cursor).order_by(Sku.id).limit(PAGE_SIZE + 1)))
    return {"items": [view(row, SKU_FIELDS) for row in rows[:PAGE_SIZE]],
            "next_cursor": rows[PAGE_SIZE - 1].id if len(rows) > PAGE_SIZE else None}


@router.put("/products/{product_id}")
async def update_product(product_id: str, payload: schemas.ProductUpdate, ctx=require("catalog:write")):
    return await command(ctx, "catalog.product_update:" + product_id, payload=payload,
                         action=lambda: CatalogService(ctx.db).update_product(product_id, payload))


@router.get("")
async def products(cursor: str = "", ctx=require("catalog:write")):
    rows = list(await ctx.db.scalars(select(Spu).where(Spu.id > cursor).order_by(Spu.id).limit(PAGE_SIZE)))
    return {"items": [view(row, SPU_FIELDS) for row in rows],
            "next_cursor": rows[-1].id if len(rows) == PAGE_SIZE else None}


@router.post("/categories")
async def category(payload: schemas.CategoryInput, ctx=require("catalog:write")):
    return await command(ctx, "catalog.category", payload=payload,
                         action=lambda: CatalogService(ctx.db).create_category(payload))


@router.post("/products")
async def product(payload: schemas.ProductInput, ctx=require("catalog:write")):
    return await command(ctx, "catalog.product", payload=payload,
                         action=lambda: CatalogService(ctx.db).create_product(payload))


@router.post("/skus")
async def sku(payload: schemas.SkuInput, ctx=require("catalog:write")):
    return await command(ctx, "catalog.sku", payload=payload,
                         action=lambda: CatalogService(ctx.db).create_sku(payload))


@router.patch("/products/{resource_id}/status")
async def product_status(resource_id: str, payload: schemas.Visibility, ctx=require("catalog:write")):
    return await command(ctx, "catalog.status:" + resource_id, payload=payload,
        action=lambda: CatalogService(ctx.db).visibility(resource_id, payload, sku=False))


@router.patch("/skus/{resource_id}/status")
async def sku_status(resource_id: str, payload: schemas.Visibility, ctx=require("catalog:write")):
    return await command(ctx, "catalog.status:" + resource_id, payload=payload,
        action=lambda: CatalogService(ctx.db).visibility(resource_id, payload, sku=True))


@router.put("/skus/{resource_id}/price")
async def price(resource_id: str, payload: schemas.PriceInput, ctx=require("catalog:write")):
    return await command(ctx, "catalog.price:" + resource_id, payload=payload,
                         action=lambda: CatalogService(ctx.db).price(resource_id, payload))
