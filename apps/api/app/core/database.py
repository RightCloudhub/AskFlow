"""Async SQLAlchemy engine and session factory."""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import event

from app.core.config import get_settings


class Base(DeclarativeBase):
    """ORM declarative base."""


def _engine_kwargs(url: str) -> dict:
    kwargs: dict = {"echo": False, "pool_pre_ping": True}
    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
        # aiosqlite has no pool_size
        kwargs.pop("pool_pre_ping", None)
    else:
        config = get_settings()
        kwargs.update(pool_size=config.db_pool_size, max_overflow=config.db_max_overflow,
                      pool_timeout=config.db_pool_timeout, pool_recycle=config.db_pool_recycle)
    return kwargs


settings = get_settings()
engine = create_async_engine(settings.database_url, **_engine_kwargs(settings.database_url))
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


def configure_sqlite(target_engine) -> None:
    if target_engine.dialect.name != "sqlite":
        return

    @event.listens_for(target_engine.sync_engine, "connect")
    def set_pragmas(connection, _record):
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute(f"PRAGMA busy_timeout={get_settings().sqlite_busy_timeout_ms}")
        if get_settings().sqlite_wal:
            cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()


configure_sqlite(engine)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db() -> None:
    """Create tables (dev/test convenience; production uses Alembic)."""
    # Import models so metadata is populated.
    from app import models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
