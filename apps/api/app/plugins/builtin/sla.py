"""SLA admin routes."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.plugins.context import AppContext


class SlaPlugin:
    id = "sla"
    depends = ["ticket"]

    def register(self, ctx: AppContext) -> None:
        from app.api.v1.admin.sla.routes import router as sla_router

        ctx.admin_router.include_router(sla_router, prefix="/sla", tags=["sla"])
