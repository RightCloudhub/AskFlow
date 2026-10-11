"""RAG + embedding + documents."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from app.plugins.types import AdminNavItem

if TYPE_CHECKING:
    from app.plugins.context import AppContext

logger = logging.getLogger("askflow.rag")


class RagPlugin:
    id = "rag"
    depends = ["core"]

    def register(self, ctx: AppContext) -> None:
        from app.api.v1.admin.documents.routes import router as documents_router
        from app.api.v1.embedding.routes import router as embedding_router
        from app.api.v1.rag.routes import router as rag_router
        from app.services.agent.pipeline.handlers.rag import handle_rag

        ctx.api_router.include_router(rag_router, prefix="/rag", tags=["rag"])
        ctx.api_router.include_router(embedding_router, prefix="/embedding", tags=["embedding"])
        ctx.admin_router.include_router(documents_router, prefix="/documents", tags=["documents"])
        ctx.register_route_handler("rag", handle_rag)
        ctx.add_nav(AdminNavItem("rag", "/admin/documents", "文档", order=20))

    async def boot(self, _ctx: AppContext) -> None:
        """Restore uploaded documents into the in-process indexes and pay the cold start now.

        Without this, documents vanished from search after a restart (D-11) and the first
        user question embedded the seed FAQ inline (TODO chat-response-latency P0).
        """
        from app.core import database as dbmod
        from app.services.knowledge.indexer.service import rehydrate_index
        from app.services.rag.bm25.index import get_default_bm25
        from app.services.rag.vector.store import ensure_seeded

        get_default_bm25()
        await ensure_seeded()
        async with dbmod.SessionLocal() as db:
            restored = await rehydrate_index(db)
        logger.info("rag boot: restored %s documents into the search index", restored)

    async def shutdown(self, _ctx: AppContext) -> None:
        """Close the pooled LLM / embedding HTTP clients."""
        from app.services.llm.client import get_llm_client
        from app.services.rag.embedding.factory import get_embedder

        await get_llm_client().aclose()
        await get_embedder().aclose()
