"""Pytest fixtures — isolated SQLite DB per test."""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

# Configure env before app import
os.environ["ASKFLOW_ENV"] = "test"
os.environ["SECRET_KEY"] = "test-secret-key-not-for-prod"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ.setdefault("ASKFLOW_PROFILE", "full")

from app.core.config import get_settings  # noqa: E402
from app.core.database import Base, get_db  # noqa: E402
from app.core import database as dbmod  # noqa: E402
from app.main import create_app  # noqa: E402
from app.plugins.runtime import set_app_context  # noqa: E402


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    os.environ["ASKFLOW_PROFILE"] = "full"
    get_settings.cache_clear()
    set_app_context(None)

    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    # Point app globals at this isolated engine (lifespan init_db + get_db)
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
    set_app_context(None)
    get_settings.cache_clear()
