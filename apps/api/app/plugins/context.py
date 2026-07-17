"""Assembly bag populated during plugin load."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from fastapi import APIRouter

from app.core.config import Settings
from app.plugins.types import AdminNavItem, SideEffectHandler, empty_admin_router, empty_api_router
from app.services.tools.registry import ToolRegistry, registry as default_tool_registry

# Route handlers are callables: TurnContext -> PipelineResult (async)
RouteHandlerFn = Callable[..., Any]


@dataclass
class AppContext:
    settings: Settings
    features: frozenset[str]
    api_router: APIRouter = field(default_factory=empty_api_router)
    admin_router: APIRouter = field(default_factory=empty_admin_router)
    tool_registry: ToolRegistry = field(default_factory=lambda: default_tool_registry)
    route_handlers: dict[str, RouteHandlerFn] = field(default_factory=dict)
    side_effect_handlers: dict[str, SideEffectHandler] = field(default_factory=dict)
    admin_nav: list[AdminNavItem] = field(default_factory=list)
    loaded_plugins: list[str] = field(default_factory=list)

    def enabled(self, plugin_id: str) -> bool:
        return plugin_id in self.features

    def add_nav(self, item: AdminNavItem) -> None:
        self.admin_nav.append(item)

    def register_route_handler(self, route: str, handler: RouteHandlerFn) -> None:
        self.route_handlers[route] = handler

    def register_side_effect(self, handler: SideEffectHandler) -> None:
        self.side_effect_handlers[handler.key] = handler
