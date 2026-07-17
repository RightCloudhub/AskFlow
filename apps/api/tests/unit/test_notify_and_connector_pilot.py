"""Pilot path: notify test-emit contract + connector invoke (shipped services)."""

from __future__ import annotations

import pytest
import httpx
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.services.connectors.service import ConnectorService
from app.services.notify.service import (
    NotifyService,
    clear_notify_sink,
    get_notify_sink,
    sign_payload,
)


class _OkTransport(httpx.AsyncBaseTransport):
    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"order_id": "O1", "status": "shipped"})


@pytest.mark.asyncio
async def test_notify_emit_signed_and_sink():
    clear_notify_sink()
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as db:
        svc = NotifyService(db)
        rec = await svc.emit("pilot.test", {"hello": "world"})
        assert rec["signature"]
        assert rec["headers"]["X-AskFlow-Signature"] == rec["signature"]
        body = __import__("json").dumps(
            rec["body"], ensure_ascii=False, separators=(",", ":")
        ).encode()
        ts = rec["headers"]["X-AskFlow-Timestamp"]
        from app.core.config import get_settings

        assert rec["signature"] == sign_payload(get_settings().secret_key, body, ts)
        assert len(get_notify_sink()) >= 1

        # unreachable URL must not raise via emit_safe
        svc.settings.notify_webhook_url = "http://127.0.0.1:9/nowhere"
        safe = await svc.emit_safe("sla.breached", {"ticket_id": "t-x"})
        assert safe is not None
    await engine.dispose()


@pytest.mark.asyncio
async def test_two_connectors_invoke_ok_and_degrade():
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
            base_url="https://orders.internal",
            path_template="/orders/{order_id}",
        )
        await svc.upsert(
            name="crm_lookup",
            base_url="https://crm.internal",
            path_template="/accounts",
        )
        ok = await svc.invoke(
            "order_status",
            params={"order_id": "O1"},
            mock_transport=_OkTransport(),
        )
        assert ok["status"] == "ok"
        assert ok["data_source"] == "connector"
        assert ok["data"]["status"] == "shipped"

        class _Fail(httpx.AsyncBaseTransport):
            async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
                return httpx.Response(502, text="bad gateway")

        mock = await svc.invoke("crm_lookup", params={}, mock_transport=_Fail())
        assert mock["status"] == "mock"
        assert mock["data_source"] == "mock"
        assert mock["data"]["mock"] is True
    await engine.dispose()
