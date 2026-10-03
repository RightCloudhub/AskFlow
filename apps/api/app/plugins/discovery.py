"""Public discovery payload for plugin / features admin UI."""

from __future__ import annotations

from typing import Any

from app.plugins.context import AppContext
from app.plugins.manifest import load_manifest_raw

EMPTY_FEATURES_VIEW: dict[str, Any] = {
    "profile": "unknown",
    "features": [],
    "loaded": [],
    "feature_deltas": "",
    "profiles": [],
    "plugins": [],
    "admin_nav": [],
    "route_handlers": [],
    "side_effects": [],
}


def _plugin_catalog(enabled: set[str], loaded: set[str]) -> list[dict[str, Any]]:
    data = load_manifest_raw()
    plugins_meta: dict[str, Any] = data.get("plugins") or {}
    catalog: list[dict[str, Any]] = []
    for pid in sorted(plugins_meta.keys()):
        meta = plugins_meta[pid] or {}
        catalog.append(
            {
                "id": pid,
                "depends": list(meta.get("depends") or []),
                "enabled": pid in enabled,
                "loaded": pid in loaded,
            }
        )
    return catalog


def _profile_names() -> list[str]:
    data = load_manifest_raw()
    return sorted((data.get("profiles") or {}).keys())


def features_public_view(ctx: AppContext) -> dict[str, Any]:
    """Runtime enablement + manifest catalog for Admin 插件管理页."""
    enabled = set(ctx.features)
    loaded = set(ctx.loaded_plugins)
    return {
        "profile": ctx.settings.askflow_profile,
        "features": sorted(ctx.features),
        "loaded": list(ctx.loaded_plugins),
        "feature_deltas": ctx.settings.askflow_features or "",
        "profiles": _profile_names(),
        "plugins": _plugin_catalog(enabled, loaded),
        "admin_nav": [
            {
                "plugin_id": n.plugin_id,
                "to": n.to,
                "label": n.label,
                "order": n.order,
            }
            for n in sorted(ctx.admin_nav, key=lambda x: (x.order, x.to))
        ],
        "route_handlers": sorted(ctx.route_handlers.keys()),
        "side_effects": sorted(ctx.side_effect_handlers.keys()),
    }


__all__ = ["EMPTY_FEATURES_VIEW", "features_public_view"]
