"""SLA engine + notify signing (enterprise §12.2)."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.core.security import hash_password
from app.models.enums import TicketPriority, TicketStatus, UserRole
from app.models.ticket import Ticket
from app.models.user import User
from app.services.notify.service import NotifyService, clear_notify_sink, get_notify_sink, sign_payload
from app.services.ticket.sla.engine import SLAEngine


@pytest.mark.asyncio
async def test_sla_warning_then_breached():
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with factory() as db:
        user = User(
            username="sla_u",
            email="sla@e.com",
            hashed_password=hash_password("password123"),
            role=UserRole.USER.value,
        )
        db.add(user)
        await db.flush()
        t = Ticket(
            user_id=user.id,
            title="urgent ticket",
            description="x",
            priority=TicketPriority.URGENT.value,
            status=TicketStatus.PENDING.value,
        )
        db.add(t)
        await db.flush()
        # backdate created_at past warning for urgent (15 min FR, warn at 70%)
        t.created_at = datetime.now(UTC) - timedelta(minutes=12)
        await db.flush()

        engine_sla = SLAEngine(db, now_fn=lambda: datetime.now(UTC))
        changes = await engine_sla.scan()
        await db.refresh(t)
        assert t.sla_state in {"warning", "breached"}
        assert any(c.ticket_id == t.id for c in changes)

        t.created_at = datetime.now(UTC) - timedelta(minutes=20)
        t.sla_state = "ok"
        await db.flush()
        changes2 = await engine_sla.scan()
        await db.refresh(t)
        assert t.sla_state == "breached"
        assert any(c.current == "breached" for c in changes2)

        # Sticky: responding does not heal BREACHED back to ok
        t.first_responded_at = datetime.now(UTC)
        t.created_at = datetime.now(UTC)  # resolve SLA not due
        await db.flush()
        await engine_sla.scan()
        await db.refresh(t)
        assert t.sla_state == "breached"

    await engine.dispose()


@pytest.mark.asyncio
async def test_notify_signed_sink_non_blocking():
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
        rec = await svc.emit_safe("ticket.created", {"ticket_id": "t1"})
        assert rec is not None
        assert rec["signature"]
        body = __import__("json").dumps(rec["body"], ensure_ascii=False, separators=(",", ":")).encode()
        ts = rec["headers"]["X-AskFlow-Timestamp"]
        from app.core.config import get_settings

        expected = sign_payload(get_settings().secret_key, body, ts)
        assert rec["signature"] == expected
        sink = get_notify_sink()
        assert len(sink) >= 1
        # emit_safe must not raise even on bad url
        svc.settings.notify_webhook_url = "http://127.0.0.1:1/nope"
        rec2 = await svc.emit_safe("sla.breached", {"ticket_id": "t2"})
        assert rec2 is not None  # still sink-recorded

    await engine.dispose()
