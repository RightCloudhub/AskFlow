"""Features discovery exposes profile + loaded plugins (runtime enablement)."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.core.config import get_settings
from app.plugins.loader import features_public_view, load_plugins
from app.plugins.runtime import set_app_context


def test_features_public_view_full_profile(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ASKFLOW_PROFILE", "full")
    get_settings.cache_clear()
    set_app_context(None)
    ctx = load_plugins(get_settings())
    view = features_public_view(ctx)
    assert view["profile"] == "full"
    assert "core" in view["features"]
    assert "rag" in view["features"]
    assert len(view["loaded"]) >= 5
    assert "rag" in view["route_handlers"]
    assert any(n["to"] == "/admin/documents" for n in view["admin_nav"])
    set_app_context(None)


def test_features_public_view_core_only(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ASKFLOW_PROFILE", "core-only")
    get_settings.cache_clear()
    set_app_context(None)
    ctx = load_plugins(get_settings())
    view = features_public_view(ctx)
    assert view["profile"] == "core-only"
    assert view["features"] == ["core"]
    assert "rag" not in view["route_handlers"]
    set_app_context(None)
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_root_exposes_profile(client: AsyncClient) -> None:
    r = await client.get("/")
    assert r.status_code == 200
    body = r.json()
    assert body.get("profile")
    assert "version" in body
