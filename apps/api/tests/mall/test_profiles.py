"""Profile isolation is verified by actual HTTP dispatch, including disabled routes."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import get_settings
from app.main import create_app
from app.plugins.runtime import get_app_context, set_app_context

PROFILES = [("full", False), ("enterprise", False), ("mvp", False),
            ("faq-only", False), ("core-only", False), ("mall", True),
            ("mall-lite", True), ("mall-only", True)]


@pytest.mark.parametrize("profile,mall", PROFILES)
async def test_profile_route_visibility(monkeypatch, profile, mall):
    monkeypatch.setenv("ASKFLOW_PROFILE", profile)
    monkeypatch.setenv("ASKFLOW_FEATURES", "")
    monkeypatch.setenv("ASKFLOW_INFRA", "lite")
    get_settings.cache_clear()
    set_app_context(None)
    try:
        app = create_app()
        await assert_http_routes(app, mall)
    finally:
        ctx = get_app_context()
        if ctx and ctx.services.get("mall_infra"):
            await ctx.services["mall_infra"].close()
        set_app_context(None)
        get_settings.cache_clear()


async def assert_http_routes(app, mall):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        for path in ("/api/v1/mall/order/orders", "/internal/mall/orders/lookup?order_id=x&customer_id=x"):
            response = await client.get(path)
            assert response.status_code == (401 if mall else 404)
        response = await client.post("/api/v1/admin/mall/wallet/adjustments", json={})
        assert response.status_code == (401 if mall else 404)
