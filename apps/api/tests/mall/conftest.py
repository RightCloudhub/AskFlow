"""Same business suite on file SQLite and an opt-in PostgreSQL/Redis test stack."""

import os
from dataclasses import dataclass
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core import database
from app.core.config import get_settings
from app.main import create_app
from app.migrations.mall_v1.integrity import install
from app.plugins.runtime import get_app_context, set_app_context


@dataclass
class MallRuntime:
    client: AsyncClient
    sessions: object
    preset: str


def configure(monkeypatch, tmp_path, preset, *, profile="mall-only"):
    url = os.environ.get("MALL_TEST_DATABASE_URL", "") if preset == "full" else "sqlite+aiosqlite:///" + str(tmp_path / "mall.db")
    if not url:
        if os.environ.get("MALL_REQUIRE_FULL") == "1":
            pytest.fail("MALL_REQUIRE_FULL requires explicit PostgreSQL and Redis test URLs")
        pytest.skip("full suite requires MALL_TEST_DATABASE_URL and MALL_TEST_REDIS_URL")
    values = {"DATABASE_URL": url, "ASKFLOW_PROFILE": profile, "ASKFLOW_INFRA": preset,
        "ASKFLOW_ENV": "test", "ASKFLOW_FEATURES": "", "MALL_PUBLIC_REGISTER": "true",
        "SEARCH_BACKEND": "like", "OBJECT_STORE": "local", "LOCAL_OBJECT_DIR": str(tmp_path / "objects"),
        "MALL_RATE_LIMIT_ENABLED": "false", "RATE_LIMIT_PER_MINUTE": "100000", "MALL_WORKER_ENABLED": "false",
        "MALL_LOGIN_MIN_SECONDS": "0", "SQLITE_BUSY_TIMEOUT_MS": "60000", "DATABASE_READ_URLS": "",
        "REDIS_URL": os.environ.get("MALL_TEST_REDIS_URL", "redis://localhost:6379/15")}
    for name, value in values.items():
        monkeypatch.setenv(name, value)
    get_settings.cache_clear()
    set_app_context(None)
    return url


async def test_engine(url):
    schema = "mall_test_" + uuid4().hex
    options = {} if url.startswith("sqlite") else {"connect_args": {"server_settings": {"search_path": schema}}}
    engine = create_async_engine(url, **options)
    database.configure_sqlite(engine)
    async with engine.begin() as connection:
        if engine.dialect.name != "sqlite":
            await connection.execute(text('CREATE SCHEMA "' + schema + '"'))
        await connection.run_sync(database.Base.metadata.create_all)
        await connection.run_sync(install)
    return engine, schema


@pytest_asyncio.fixture(params=["lite", "full"])
async def mall_runtime(request, monkeypatch, tmp_path):
    marker = request.node.get_closest_marker("mall_profile")
    profile = marker.args[0] if marker else "mall-only"
    url = configure(monkeypatch, tmp_path, request.param, profile=profile)
    application = create_app()
    engine, schema = await test_engine(url)
    previous = database.engine, database.SessionLocal
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    database.engine, database.SessionLocal = engine, sessions
    try:
        if request.param == "full":
            assert await get_app_context().services["mall_infra"].redis.client().ping()
        transport = ASGITransport(app=application)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield MallRuntime(client=client, sessions=sessions, preset=request.param)
    finally:
        ctx = get_app_context()
        if ctx and ctx.services.get("mall_infra"):
            await ctx.services["mall_infra"].close()
        if engine.dialect.name != "sqlite":
            async with engine.begin() as connection:
                await connection.execute(text('DROP SCHEMA "' + schema + '" CASCADE'))
        await engine.dispose()
        database.engine, database.SessionLocal = previous
        set_app_context(None)
        get_settings.cache_clear()
