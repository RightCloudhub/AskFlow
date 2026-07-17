"""Knowledge gap + drafts + gap side-effect."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.plugins.types import AdminNavItem

if TYPE_CHECKING:
    from app.plugins.context import AppContext


class KnowledgePlugin:
    id = "knowledge"
    depends = ["rag"]

    def register(self, ctx: AppContext) -> None:
        from app.api.v1.admin.drafts.routes import router as drafts_router
        from app.api.v1.admin.gaps.routes import router as gaps_router
        from app.services.chat.side_effects.gap import GapSideEffect

        ctx.admin_router.include_router(gaps_router, prefix="/gaps", tags=["gaps"])
        ctx.admin_router.include_router(drafts_router, prefix="/drafts", tags=["drafts"])
        ctx.register_side_effect(GapSideEffect())
        ctx.add_nav(AdminNavItem("knowledge", "/admin/gaps", "缺口", order=30))
        ctx.add_nav(AdminNavItem("knowledge", "/admin/drafts", "草稿", order=31))
