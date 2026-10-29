"""Port behavior, optional Redis implementation and upload boundaries."""

from uuid import uuid4

import pytest

from app.commerce.core.errors import MallError
from app.commerce.infra.cache import MemoryCache, OffCache
from app.commerce.infra.objects import image_key
from app.commerce.infra.runtime import infra


@pytest.mark.asyncio
async def test_ttl_lru_and_off(monkeypatch):
    monkeypatch.setattr("app.commerce.infra.cache.time.monotonic", lambda: 10)
    cache = MemoryCache(1)
    await cache.put("first", None, ttl=2)
    assert await cache.get("first") == (True, None)
    await cache.put("second", {"value": 1}, ttl=2)
    assert await cache.get("first") == (False, None)
    monkeypatch.setattr("app.commerce.infra.cache.time.monotonic", lambda: 13)
    assert await cache.get("second") == (False, None)
    assert await OffCache().get("anything") == (False, None)


@pytest.mark.asyncio
async def test_selected_limiter_never_exceeds_limit(mall_runtime):
    key = "test:" + str(uuid4())
    results = [await infra().limits.allow(key, limit=2, window=60) for _ in range(5)]
    assert results == [True, True, False, False, False]


@pytest.mark.parametrize("body,kind", [(b"<svg onload=alert(1)>", "image/svg+xml"),
    (b"javascript", "image/png"), (b"", "image/png")])
def test_upload_spoofing_is_rejected(body, kind):
    with pytest.raises(MallError):
        image_key(body, content_type=kind, maximum=100)
