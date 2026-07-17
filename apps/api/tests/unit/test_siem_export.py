"""SIEM event shape + push skipped without webhook."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.config import Settings
from app.core.database import Base
from app.services.audit.logger.service import AuditService
from app.services.audit.siem import SiemExportService, audit_to_siem_event


def test_audit_to_siem_event_shape():
    row = SimpleNamespace(
        id="a1",
        action="widget.session_open",
        resource_type="conversation",
        resource_id="c1",
        actor_id="u1",
        detail={"visitor_key": "v"},
        ip=None,
        trace_id=None,
        created_at=None,
    )
    ev = audit_to_siem_event(row)
    assert ev["source"] == "askflow"
    assert ev["event_type"] == "audit"
    assert ev["action"] == "widget.session_open"
    assert ev["detail"]["visitor_key"] == "v"


@pytest.mark.asyncio
async def test_siem_export_and_skip_push():
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as db:
        await AuditService(db).log(
            action="test.siem",
            resource_type="system",
            resource_id=None,
            actor_id=None,
            detail={"k": 1},
        )
        settings = Settings(
            ASKFLOW_ENV="test",
            SECRET_KEY="test-secret-key-not-for-prod-xx",
            SIEM_WEBHOOK_URL=None,
        )
        svc = SiemExportService(db, settings=settings)
        events = await svc.export_events(limit=10)
        assert any(e["action"] == "test.siem" for e in events)
        delivery = await svc.push_to_webhook(events)
        assert delivery["status"] == "skipped"
    await engine.dispose()
