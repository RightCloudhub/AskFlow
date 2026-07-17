"""Quality check admin (PRD E8)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.plugins.types import AdminNavItem

if TYPE_CHECKING:
    from app.plugins.context import AppContext


class QcPlugin:
    id = "qc"
    depends = ["analytics"]

    def register(self, ctx: AppContext) -> None:
        from app.api.v1.admin.qc.routes import router as qc_router

        ctx.admin_router.include_router(qc_router, prefix="/qc", tags=["qc"])
        ctx.add_nav(AdminNavItem("qc", "/admin/qc", "质检", order=15))
