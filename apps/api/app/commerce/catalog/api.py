"""Public storefront reads never return inactive products."""

from http import HTTPStatus
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Request
from sqlalchemy import select

from app.commerce.catalog.models import Category
from app.commerce.catalog.schemas import Search
from app.commerce.catalog.search import search
from app.commerce.catalog.service import CatalogService
from app.commerce.core.deps import MallDb
from app.commerce.core.errors import MallError
from app.commerce.core.schemas import view
from app.commerce.infra.database import read_session
from app.commerce.infra.runtime import infra

router = APIRouter()


@router.get("/categories")
async def categories(db: MallDb):
    rows = await db.scalars(select(Category).where(Category.active).order_by(Category.id))
    return {"items": [view(row, ("id", "name", "slug", "parent_id")) for row in rows]}


@router.get("/search")
async def products(payload: Annotated[Search, Query()], db: MallDb, request: Request):
    async with read_session(db, sticky=request.headers.get("x-mall-read-primary") == "1") as reader:
        return await search(reader, payload)


@router.get("/products/{spu_id}")
async def product(spu_id: UUID, db: MallDb):
    async def load():
        try:
            return await CatalogService(db).detail(str(spu_id))
        except MallError as exc:
            if exc.status != 404:
                raise
            return None

    result = await infra().cache.get("product:" + str(spu_id), load)
    if result is None:
        raise MallError("resource_not_found", status=HTTPStatus.NOT_FOUND)
    return result
