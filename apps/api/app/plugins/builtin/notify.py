"""Notify channel — admin test-emit + ticket/SLA hooks."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.plugins.context import AppContext


class NotifyPlugin:
    id = "notify"
    depends = ["core"]

    def register(self, ctx: AppContext) -> None:
        from app.api.v1.admin.notify.routes import router as notify_router

        ctx.admin_router.include_router(notify_router, prefix="/notify", tags=["notify"])
