"""Disabled domains must not acquire public or administration routes."""

import pytest

from app.core.config import get_settings
from app.main import create_app
from app.plugins.runtime import set_app_context


@pytest.mark.parametrize("profile,mall", [("full", False), ("enterprise", False), ("mvp", False),
    ("faq-only", False), ("core-only", False), ("mall", True), ("mall-lite", True), ("mall-only", True)])
def test_profile_route_visibility(monkeypatch, profile, mall):
    monkeypatch.setenv("ASKFLOW_PROFILE", profile)
    monkeypatch.setenv("ASKFLOW_FEATURES", "")
    monkeypatch.setenv("ASKFLOW_INFRA", "lite")
    get_settings.cache_clear()
    set_app_context(None)
    try:
        app = create_app()
        paths = {getattr(route, "path", "") for route in app.routes}
        assert ("/api/v1/mall/order/orders" in paths) is mall
        assert ("/api/v1/admin/mall/wallet/adjustments" in paths) is mall
        assert ("/internal/mall/orders/lookup" in paths) is mall
    finally:
        set_app_context(None)
        get_settings.cache_clear()
