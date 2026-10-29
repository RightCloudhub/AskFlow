"""Audited catalog management; no client-selected prices at checkout."""

from fastapi import APIRouter
from sqlalchemy import select

from app.commerce.admin.permissions import require
from app.commerce.catalog import schemas
from app.commerce.catalog.models import Spu
from app.commerce.catalog.service import CatalogService, SPU_FIELDS
from app.commerce.core.commands import command
from app.commerce.core.constants import PAGE_SIZE
from app.commerce.core.schemas import view

router = APIRouter()


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
