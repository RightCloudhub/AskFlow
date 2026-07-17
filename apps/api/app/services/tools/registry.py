"""Central tool registry — only registered handlers may execute (PRD + MCP whitelist)."""

from __future__ import annotations

from typing import Any, Awaitable, Callable

from app.services.tools.search_order.handler import search_order
from app.services.tools.search_knowledge.handler import search_knowledge

ToolHandler = Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]


class ToolRegistry:
    def __init__(self) -> None:
        self._handlers: dict[str, ToolHandler] = {
            "search_order": search_order,
            "search_knowledge": search_knowledge,
        }
        self._mcp_tools: set[str] = set()

    def get(self, name: str) -> ToolHandler | None:
        return self._handlers.get(name)

    def names(self) -> list[str]:
        return sorted(self._handlers)

    def as_loop_map(self) -> dict[str, ToolHandler]:
        return dict(self._handlers)

    def register(
        self,
        name: str,
        handler: ToolHandler,
        *,
        source: str = "builtin",
        whitelist: set[str] | None = None,
    ) -> bool:
        """Register tool only if name is in whitelist when provided (MCP path)."""
        if whitelist is not None and name not in whitelist:
            return False
        self._handlers[name] = handler
        if source == "mcp":
            self._mcp_tools.add(name)
        return True

    def is_mcp(self, name: str) -> bool:
        return name in self._mcp_tools


registry = ToolRegistry()


async def register_mcp_tools_from_settings(db=None) -> list[str]:
    """Import MCP tools into registry when MCP_ENABLED (whitelist-only)."""
    from app.core.config import get_settings
    from app.services.audit.logger.service import AuditService

    settings = get_settings()
    if not settings.mcp_enabled:
        return []
    whitelist = {p.strip() for p in settings.mcp_tool_whitelist.split(",") if p.strip()}
    registered: list[str] = []

    # MCP tools are wrappers; only whitelist names may bind to existing or stub handlers
    async def _mcp_echo(args: dict[str, Any]) -> dict[str, Any]:
        return {"status": "ok", "data_source": "mcp", "data": args}

    for name in whitelist:
        if name in registry.names() and name not in {"search_order"}:
            # already present (e.g. search_knowledge) — mark as mcp-approved
            registry._mcp_tools.add(name)
            registered.append(name)
            continue
        if name not in registry.names():
            ok = registry.register(name, _mcp_echo, source="mcp", whitelist=whitelist)
            if ok:
                registered.append(name)
        else:
            registered.append(name)

    if db is not None and registered:
        await AuditService(db).log(
            action="mcp.tools_register",
            resource_type="tool_registry",
            resource_id="mcp",
            detail={"tools": registered, "whitelist": sorted(whitelist)},
        )
    return registered
