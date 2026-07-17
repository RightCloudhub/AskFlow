"""Web widget guest channel (PRD E7a)."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.plugins.context import AppContext


class WidgetPlugin:
    id = "widget"
    depends = ["core"]

    def register(self, ctx: AppContext) -> None:
        from app.api.v1.widget.routes import router as widget_router

        ctx.api_router.include_router(widget_router, prefix="/widget", tags=["widget"])
