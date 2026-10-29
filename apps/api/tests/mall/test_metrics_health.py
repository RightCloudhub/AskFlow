"""Live inventory metrics and complete, secret-free readiness projections."""

import pytest
from sqlalchemy import text, update

from app.commerce.core.errors import MallError
from app.commerce.infra import health
from app.commerce.infra.metrics import OVERSOLD, STOCK_ATTEMPTS, STOCK_SHORTAGE
from app.commerce.inventory.models import Inventory
from app.commerce.inventory.observability import snapshot

from .helpers import place, seed, transaction


async def test_insufficient_stock_increments_both_counters(mall_runtime):
    identity = await seed(mall_runtime, stock=0)
    attempts = STOCK_ATTEMPTS._value.get()
    failures = STOCK_SHORTAGE._value.get()
    with pytest.raises(MallError, match="inventory_insufficient"):
        await transaction(mall_runtime, lambda db: place(db, identity))
    assert STOCK_ATTEMPTS._value.get() == attempts + 1
    assert STOCK_SHORTAGE._value.get() == failures + 1


async def test_negative_stock_updates_oversold_metric(mall_runtime):
    if mall_runtime.preset != "lite":
        pytest.skip("Deliberate SQLite constraint bypass; PostgreSQL rejects this corruption")
    identity = await seed(mall_runtime)
    async with mall_runtime.sessions() as db:
        await db.execute(text("PRAGMA ignore_check_constraints=ON"))
        await db.execute(update(Inventory).where(Inventory.sku_id == identity["sku_id"]).values(available=-3))
        report = await snapshot(db)
        assert report["oversold_units"] == 3
        assert report["negative_inventory"] == 1
        assert OVERSOLD._value.get() == 3
        await db.rollback()
    OVERSOLD.set(0)


async def test_health_matrix_and_critical_dependency_failure(mall_runtime, monkeypatch):
    response = await mall_runtime.client.get("/health/ready")
    assert response.status_code == 200, response.text
    ports = {row["port"] for row in response.json()["ports"]}
    assert ports == {"database", "cache", "lock", "rate_limit", "event_bus", "search",
                     "object_store", "sessions", "email", "sms", "workers", "flash_sale"}
    assert "redis://" not in response.text and "sqlite+" not in response.text

    async def unavailable():
        raise ConnectionError("do not disclose this connection detail")

    monkeypatch.setattr(health, "database_up", unavailable)
    for path in ("/health/ready", "/health"):
        response = await mall_runtime.client.get(path)
        assert response.status_code == 503
        assert "do not disclose" not in response.text
    assert (await mall_runtime.client.get("/health/live")).status_code == 200
