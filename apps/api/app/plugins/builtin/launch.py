"""Launch Card admin."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.plugins.types import AdminNavItem

if TYPE_CHECKING:
    from app.plugins.context import AppContext


class LaunchPlugin:
    id = "launch"
    depends = ["core"]

    def register(self, ctx: AppContext) -> None:
        from app.api.v1.admin.launch_cards.routes import router as launch_cards_router

        ctx.admin_router.include_router(
            launch_cards_router, prefix="/launch-cards", tags=["launch-cards"]
        )
        ctx.add_nav(AdminNavItem("launch", "/admin/launch-cards", "Launch", order=94))
