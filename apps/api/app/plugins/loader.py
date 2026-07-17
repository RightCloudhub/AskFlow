"""Load enabled plugins, register, optional boot."""

from __future__ import annotations

import logging
from typing import Any

from app.core.config import Settings, get_settings
from app.plugins.builtin import create_builtin
from app.plugins.context import AppContext
from app.plugins.manifest import ManifestError, resolve_features, topological_order
from app.plugins.runtime import set_app_context

logger = logging.getLogger("askflow.plugins")


def load_plugins(settings: Settings | None = None) -> AppContext:
    """Resolve features, instantiate builtins, register into AppContext."""
    settings = settings or get_settings()
    features = resolve_features(
        settings.askflow_profile,
        settings.askflow_features,
    )
    order = topological_order(features)
    ctx = AppContext(settings=settings, features=features)

    for pid in order:
        plugin = create_builtin(pid)
        plugin.register(ctx)
        ctx.loaded_plugins.append(pid)
        logger.info("plugin registered id=%s", pid)

    # Always mount admin under api once plugins have filled it
    ctx.api_router.include_router(ctx.admin_router)
    set_app_context(ctx)
    return ctx


async def boot_plugins(ctx: AppContext) -> None:
    for pid in ctx.loaded_plugins:
        plugin = create_builtin(pid)
        boot = getattr(plugin, "boot", None)
        if boot is None:
            continue
        result = boot(ctx)
        if hasattr(result, "__await__"):
            await result  # type: ignore[misc]


async def shutdown_plugins(ctx: AppContext | None) -> None:
    if ctx is None:
        return
    for pid in reversed(ctx.loaded_plugins):
        plugin = create_builtin(pid)
        shutdown = getattr(plugin, "shutdown", None)
        if shutdown is None:
            continue
        result = shutdown(ctx)
        if hasattr(result, "__await__"):
            await result  # type: ignore[misc]
    set_app_context(None)


def features_public_view(ctx: AppContext) -> dict[str, Any]:
    return {
        "profile": ctx.settings.askflow_profile,
        "features": sorted(ctx.features),
        "loaded": list(ctx.loaded_plugins),
        "admin_nav": [
            {"plugin_id": n.plugin_id, "to": n.to, "label": n.label, "order": n.order}
            for n in sorted(ctx.admin_nav, key=lambda x: (x.order, x.to))
        ],
        "route_handlers": sorted(ctx.route_handlers.keys()),
        "side_effects": sorted(ctx.side_effect_handlers.keys()),
    }


__all__ = [
    "ManifestError",
    "boot_plugins",
    "features_public_view",
    "load_plugins",
    "shutdown_plugins",
]
