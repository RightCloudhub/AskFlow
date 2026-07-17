"""Feishu IM channel (PRD E7b)."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.plugins.context import AppContext


class FeishuPlugin:
    id = "feishu"
    depends = ["core"]

    def register(self, ctx: AppContext) -> None:
        from app.api.v1.channels.feishu.routes import router as feishu_router

        ctx.api_router.include_router(feishu_router, prefix="/channels/feishu", tags=["feishu"])
