"""Ops: intents + prompts admin."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.plugins.types import AdminNavItem

if TYPE_CHECKING:
    from app.plugins.context import AppContext


class OpsPlugin:
    id = "ops"
    depends = ["core"]

    def register(self, ctx: AppContext) -> None:
        from app.api.v1.admin.bots.routes import router as bots_router
        from app.api.v1.admin.intents.routes import router as intents_router
        from app.api.v1.admin.prompts.routes import router as prompts_router

        ctx.admin_router.include_router(intents_router, prefix="/intents", tags=["intents"])
        ctx.admin_router.include_router(prompts_router, prefix="/prompts", tags=["prompts"])
        ctx.admin_router.include_router(bots_router, prefix="/bots", tags=["bots"])
        ctx.add_nav(AdminNavItem("ops", "/admin/intents", "意图", order=21))
        ctx.add_nav(AdminNavItem("ops", "/admin/prompts", "Prompt", order=22))
        ctx.add_nav(AdminNavItem("ops", "/admin/bots", "多Bot", order=23))
