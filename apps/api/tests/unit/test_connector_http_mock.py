"""Connector HTTP 4xx/5xx must degrade to mock (enterprise offline)."""

import pytest
import httpx
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.services.connectors.service import ConnectorService


class _FailTransport(httpx.AsyncBaseTransport):
    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"error": "upstream_down"})


@pytest.mark.asyncio
async def test_http_503_returns_mock_not_bare_error():
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as db:
        svc = ConnectorService(db)
        await svc.upsert(
            name="order_status",
            base_url="https://example.invalid",
            path_template="/status",
        )
        result = await svc.invoke(
            "order_status",
            params={"order_id": "X"},
            mock_transport=_FailTransport(),
        )
        assert result["status"] == "mock"
        assert result["data_source"] == "mock"
        assert result["data"]["mock"] is True
        assert "503" in result.get("message", "") or result["data"]["reason"].startswith(
            "upstream_http_"
        )
    await engine.dispose()
