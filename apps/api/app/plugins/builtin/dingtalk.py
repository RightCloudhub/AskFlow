"""DingTalk channel plugin."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.plugins.context import AppContext


class DingTalkPlugin:
    id = "dingtalk"
    depends = ["core"]

    def register(self, ctx: AppContext) -> None:
        from app.api.v1.channels.dingtalk.routes import router as dt_router

        ctx.api_router.include_router(dt_router, prefix="/channels/dingtalk", tags=["dingtalk"])
