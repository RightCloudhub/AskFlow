"""MCP tool whitelist sync admin."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.plugins.context import AppContext


class McpPlugin:
    id = "mcp"
    depends = ["tools"]

    def register(self, ctx: AppContext) -> None:
        from app.api.v1.admin.mcp.routes import router as mcp_router

        ctx.admin_router.include_router(mcp_router, prefix="/mcp", tags=["mcp"])

    async def boot(self, ctx: AppContext) -> None:
        if not ctx.settings.mcp_enabled:
            return
        from app.services.tools.registry import register_mcp_tools_from_settings

        await register_mcp_tools_from_settings(db=None)
