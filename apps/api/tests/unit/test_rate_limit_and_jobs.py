"""Rate limiter unit path + enterprise jobs run_once (no background sleep)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from app.core.config import Settings, get_settings
from app.core.database import Base
from app.core.security import hash_password
from app.middleware.rate_limit import RateLimitMiddleware
from app.models.enums import TicketPriority, TicketStatus, UserRole
from app.models.ticket import Ticket
from app.models.user import User
from app.workers.enterprise_jobs import run_once


def test_rate_limit_middleware_returns_429_when_exceeded(monkeypatch: pytest.MonkeyPatch):
    from types import SimpleNamespace

    # Avoid env=test from suite conftest short-circuiting the limiter
    monkeypatch.setattr(
        "app.middleware.rate_limit.get_settings",
        lambda: SimpleNamespace(
            env="development",
            rate_limit_per_minute=3,
            trust_proxy_headers=False,
        ),
    )

    async def homepage(_request: Request) -> PlainTextResponse:
        return PlainTextResponse("ok")

    app = Starlette(routes=[Route("/api/v1/ping", homepage)])
    app.add_middleware(RateLimitMiddleware)

    client = TestClient(app)
    codes = [client.get("/api/v1/ping").status_code for _ in range(5)]
    assert codes.count(200) == 3
    assert 429 in codes


@pytest.mark.asyncio
async def test_enterprise_jobs_run_once_sla_and_handoff():
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    import app.core.database as dbmod

    old_session = dbmod.SessionLocal
    old_engine = dbmod.engine
    dbmod.engine = engine
    dbmod.SessionLocal = factory
    try:
        async with factory() as db:
            user = User(
                username="jobs_u",
                email="jobs@e.com",
                hashed_password=hash_password("password123"),
                role=UserRole.USER.value,
            )
            db.add(user)
            await db.flush()
            t = Ticket(
                user_id=user.id,
                title="urgent open",
                description="x",
                priority=TicketPriority.URGENT.value,
                status=TicketStatus.PENDING.value,
            )
            db.add(t)
            await db.flush()
            t.created_at = datetime.now(UTC) - timedelta(minutes=20)
            await db.commit()

        result = await run_once()
        assert "handoff_swept" in result
        assert "sla_changes" in result
        assert result["sla_changes"] >= 1
    finally:
        dbmod.SessionLocal = old_session
        dbmod.engine = old_engine
        await engine.dispose()
