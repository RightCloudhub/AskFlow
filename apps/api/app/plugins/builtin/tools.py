"""Tool registry builtins + TOOL route handler."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.plugins.context import AppContext


class ToolsPlugin:
    id = "tools"
    depends = ["agent"]

    def register(self, ctx: AppContext) -> None:
        from app.services.agent.pipeline.handlers.tool import handle_tool
        from app.services.tools.registry import registry
        from app.services.tools.search_knowledge.handler import search_knowledge
        from app.services.tools.search_order.handler import search_order

        # Ensure builtins present (idempotent overwrite)
        registry.register("search_order", search_order, source="builtin")
        registry.register("search_knowledge", search_knowledge, source="builtin")
        ctx.tool_registry = registry
        ctx.register_route_handler("tool", handle_tool)
