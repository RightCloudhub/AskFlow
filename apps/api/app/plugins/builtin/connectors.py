"""Business connectors admin."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.plugins.types import AdminNavItem

if TYPE_CHECKING:
    from app.plugins.context import AppContext


class ConnectorsPlugin:
    id = "connectors"
    depends = ["core"]

    def register(self, ctx: AppContext) -> None:
        from app.api.v1.admin.connectors.routes import router as connectors_router

        ctx.admin_router.include_router(
            connectors_router, prefix="/connectors", tags=["connectors"]
        )
        ctx.add_nav(AdminNavItem("connectors", "/admin/connectors", "连接器", order=92))
