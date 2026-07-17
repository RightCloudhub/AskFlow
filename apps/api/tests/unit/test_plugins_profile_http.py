"""HTTP surface converges by ASKFLOW_PROFILE."""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

os.environ.setdefault("ASKFLOW_ENV", "test")
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-prod")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")


async def _make_client(profile: str) -> AsyncGenerator[AsyncClient, None]:
    os.environ["ASKFLOW_PROFILE"] = profile
    from app.core.config import get_settings
    from app.core.database import Base, get_db
    from app.core import database as dbmod
    from app.main import create_app
    from app.plugins.runtime import set_app_context

    get_settings.cache_clear()
    set_app_context(None)

    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    old_engine = dbmod.engine
    old_session = dbmod.SessionLocal
    dbmod.engine = engine
    dbmod.SessionLocal = session_factory

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async def _override_db() -> AsyncGenerator[AsyncSession, None]:
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    application = create_app()
    application.dependency_overrides[get_db] = _override_db
    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    application.dependency_overrides.clear()
    await engine.dispose()
    dbmod.engine = old_engine
    dbmod.SessionLocal = old_session
    get_settings.cache_clear()
    set_app_context(None)
    os.environ["ASKFLOW_PROFILE"] = "full"


@pytest_asyncio.fixture
async def core_client() -> AsyncGenerator[AsyncClient, None]:
    async for c in _make_client("core-only"):
        yield c


@pytest.mark.asyncio
async def test_core_only_hides_rag_and_tickets(core_client: AsyncClient) -> None:
    # unauthenticated may 401/403; disabled routes should be 404 not 401
    r = await core_client.get("/api/v1/rag/query")
    # FastAPI: missing route → 404; method not allowed etc.
    assert r.status_code == 404

    r2 = await core_client.get("/api/v1/tickets")
    assert r2.status_code == 404

    # health still present
    h = await core_client.get("/health")
    assert h.status_code == 200

    # chat still present (401 without auth is ok; not 404)
    ch = await core_client.get("/api/v1/chat/conversations")
    assert ch.status_code != 404
