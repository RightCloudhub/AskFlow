"""Search IDs only; catalog service re-applies visibility, filters and pricing."""

import httpx
from sqlalchemy import func, select, text

from app.commerce.core.constants import MAX_PAGE_SIZE


def complete_candidates(ids):
    # A bounded search hint must never truncate authoritative keyset pagination.
    return ids if len(ids) <= MAX_PAGE_SIZE else None


class DatabaseSearch:
    def __init__(self, backend: str):
        self.backend = backend

    async def ids(self, db, query: str):
        if not query or self.backend == "like":
            return None
        if self.backend == "sqlite_fts":
            return await self._sqlite(db, query)
        from app.commerce.catalog.models import Spu

        statement = select(Spu.id).where(
            func.to_tsvector("simple", Spu.title + " " + Spu.description).op("@@")(
                func.plainto_tsquery("simple", query)))
        return complete_candidates(list(await db.scalars(statement.limit(MAX_PAGE_SIZE + 1))))

    async def _sqlite(self, db, query):
        if db.bind.dialect.name != "sqlite":
            return None
        # Quoted literal search terms prevent caller-supplied FTS operators.
        escaped = '"' + query.replace('"', '""') + '"'
        result = await db.execute(text(
            "SELECT spu_id FROM mall_catalog_fts WHERE mall_catalog_fts MATCH :query LIMIT :limit"
        ), {"query": escaped, "limit": MAX_PAGE_SIZE + 1})
        return complete_candidates([row[0] for row in result])


class ElasticSearch:
    def __init__(self, settings, breaker):
        self.settings, self.breaker = settings, breaker

    async def ids(self, db, query: str):
        if not query:
            return None

        async def request():
            async with httpx.AsyncClient(timeout=self.settings.external_timeout_seconds) as client:
                response = await client.post(self.settings.search_url.rstrip("/") + "/mall/_search",
                    json={"size": MAX_PAGE_SIZE + 1, "query": {"multi_match": {
                        "query": query, "fields": ["title", "description"]}}})
                response.raise_for_status()
                return complete_candidates([hit["_id"] for hit in response.json()["hits"]["hits"]])

        return await self.breaker.call(request)
