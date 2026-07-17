"""Plugin manifest + loader unit tests."""

from __future__ import annotations

import os

import pytest

from app.plugins.manifest import (
    ManifestError,
    clear_manifest_cache,
    parse_feature_deltas,
    resolve_features,
    topological_order,
)


def setup_function() -> None:
    clear_manifest_cache()


def test_resolve_full_profile() -> None:
    feats = resolve_features("full", None)
    assert "core" in feats
    assert "mcp" in feats
    assert "rag" in feats


def test_resolve_core_only() -> None:
    feats = resolve_features("core-only", None)
    assert feats == frozenset({"core"})


def test_delta_add_remove() -> None:
    feats = resolve_features("mvp", "-tools,+sla")
    # tools removed; sla needs ticket which is in mvp
    assert "tools" not in feats
    assert "sla" in feats
    assert "ticket" in feats
    # agent stays (not removed)
    assert "agent" in feats


def test_delta_add_pulls_deps() -> None:
    feats = resolve_features("core-only", "+mcp")
    assert "mcp" in feats
    assert "tools" in feats
    assert "agent" in feats
    assert "core" in feats


def test_unknown_profile() -> None:
    with pytest.raises(ManifestError):
        resolve_features("nope", None)


def test_topo_order_respects_deps() -> None:
    feats = resolve_features("mvp", None)
    order = topological_order(feats)
    assert order.index("core") < order.index("rag")
    assert order.index("agent") < order.index("tools")


def test_parse_deltas() -> None:
    add, rem = parse_feature_deltas("+sla,-mcp,teams")
    assert add == {"sla", "teams"}
    assert rem == {"mcp"}


def test_loader_full_registers_routes(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.config import get_settings
    from app.plugins.loader import load_plugins
    from app.plugins.runtime import set_app_context

    monkeypatch.setenv("ASKFLOW_PROFILE", "full")
    get_settings.cache_clear()
    set_app_context(None)
    ctx = load_plugins(get_settings())
    assert "core" in ctx.loaded_plugins
    assert "rag" in ctx.route_handlers
    assert "ticket" in ctx.side_effect_handlers
    paths = [str(getattr(r, "path", r)) for r in ctx.api_router.routes]
    joined = " ".join(paths)
    # chat is mounted with prefix on include_router; path may be /conversations etc.
    assert ctx.api_router.routes, "api_router should have routes"
    assert any(
        "conversation" in p or "health" in p or "tickets" in p or "rag" in p
        for p in paths
    ) or len(ctx.api_router.routes) > 5, joined


def test_loader_core_only_no_tickets(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.config import get_settings
    from app.plugins.loader import load_plugins
    from app.plugins.runtime import set_app_context

    monkeypatch.setenv("ASKFLOW_PROFILE", "core-only")
    get_settings.cache_clear()
    set_app_context(None)
    ctx = load_plugins(get_settings())
    assert ctx.loaded_plugins == ["core"]
    assert "rag" not in ctx.route_handlers
    assert "ticket" not in ctx.side_effect_handlers
