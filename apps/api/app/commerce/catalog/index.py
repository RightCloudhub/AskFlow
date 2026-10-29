"""Committed catalog events invalidate shared cache and synchronize search indexes."""

import httpx
from sqlalchemy import text

from app.commerce.catalog.models import Spu
from app.commerce.infra.runtime import infra
from app.core.config import get_settings


async def synchronize(db, spu_id: str):
    await infra().cache.delete("product:" + spu_id)
    row = await db.get(Spu, spu_id)
    settings = get_settings()
    if settings.search_backend == "elasticsearch":
        async with httpx.AsyncClient(timeout=settings.external_timeout_seconds) as client:
            response = await client.put(settings.search_url.rstrip("/") + "/mall/_doc/" + spu_id,
                json={"title": row.title, "description": row.description, "status": row.status})
            response.raise_for_status()
    if settings.search_backend == "sqlite_fts" and db.bind.dialect.name == "sqlite":
        await db.execute(text("CREATE VIRTUAL TABLE IF NOT EXISTS mall_catalog_fts USING fts5(spu_id UNINDEXED, title, description)"))
        await db.execute(text("DELETE FROM mall_catalog_fts WHERE spu_id=:id"), {"id": spu_id})
        await db.execute(text("INSERT INTO mall_catalog_fts(spu_id,title,description) VALUES(:id,:title,:description)"),
            {"id": spu_id, "title": row.title, "description": row.description})
