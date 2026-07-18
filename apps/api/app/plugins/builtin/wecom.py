"""WeCom channel plugin."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.plugins.context import AppContext


class WeComPlugin:
    id = "wecom"
    depends = ["core"]

    def register(self, ctx: AppContext) -> None:
        from app.api.v1.channels.wecom.routes import router as wecom_router

        ctx.api_router.include_router(wecom_router, prefix="/channels/wecom", tags=["wecom"])
