"""Explicit replica reads; authentication, finance and write-after-read stay primary."""

import json
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.core.database import _engine_kwargs
from app.plugins.runtime import require_app_context


def read_factories():
    ctx = require_app_context()
    if "mall_read_factories" in ctx.services:
        return ctx.services["mall_read_factories"]
    raw = get_settings().database_read_urls.strip()
    urls = json.loads(raw) if raw.startswith("[") else [value.strip() for value in raw.split(",") if value.strip()]
    engines = [create_async_engine(url, **_engine_kwargs(url)) for url in urls]
    factories = [async_sessionmaker(engine, expire_on_commit=False) for engine in engines]
    ctx.services["mall_read_engines"], ctx.services["mall_read_factories"] = engines, factories
    return factories


@asynccontextmanager
async def read_session(primary, *, sticky: bool = False):
    factories = read_factories()
    if sticky or not factories:
        yield primary
        return
    ctx = require_app_context()
    index = ctx.services.get("mall_read_index", 0) % len(factories)
    ctx.services["mall_read_index"] = index + 1
    async with factories[index]() as replica:
        yield replica


async def close_read_engines(ctx):
    for engine in ctx.services.pop("mall_read_engines", []):
        await engine.dispose()
    ctx.services.pop("mall_read_factories", None)
