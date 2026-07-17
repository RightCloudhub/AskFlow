"""RAG + embedding + documents."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.plugins.types import AdminNavItem

if TYPE_CHECKING:
    from app.plugins.context import AppContext


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
