"""Analytics dashboard API + default admin home nav."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.plugins.types import AdminNavItem

if TYPE_CHECKING:
    from app.plugins.context import AppContext


class AnalyticsPlugin:
    id = "analytics"
    depends = ["core"]

    def register(self, ctx: AppContext) -> None:
        from app.api.v1.admin.analytics.routes import router as analytics_router

        ctx.admin_router.include_router(
            analytics_router, prefix="/analytics", tags=["analytics"]
        )
        ctx.add_nav(AdminNavItem("analytics", "/admin", "看板", order=10))
