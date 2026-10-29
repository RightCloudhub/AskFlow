"""Read-only operations view; no credentials or connection strings are exposed."""

import asyncio

from fastapi import APIRouter, Depends
from sqlalchemy import text

from app.commerce.infra.matrix import capability_matrix
from app.commerce.infra.runtime import infra
from app.core import database
from app.core.config import get_settings
from app.core.deps import require_agent_or_admin

router = APIRouter()
health_router = APIRouter()


@router.get("")
async def infrastructure(_user=Depends(require_agent_or_admin)):
    return capability_matrix(get_settings())


@health_router.get("/health/live")
async def live():
    return {"status": "ok"}


@health_router.get("/health/ready")
async def ready():
    from fastapi.responses import JSONResponse

    states = {"database": await _database_ready()}
    settings = get_settings()
    if "redis" in {settings.lock_backend, settings.rate_limit_backend, settings.flash_sale_backend}:
        states["coordination"] = await _redis_ready()
    available = all(states.values())
    return JSONResponse(status_code=200 if available else 503,
                         content={"status": "ok" if available else "down", "dependencies": states})


async def _database_ready():
    try:
        async with database.engine.connect() as connection:
            await connection.execute(text("SELECT 1 FROM idempotency_records LIMIT 1"))
        return True
    except Exception:
        return False


async def _redis_ready():
    try:
        return bool(await asyncio.wait_for(infra().redis.client().ping(),
                                          get_settings().external_timeout_seconds))
    except Exception:
        return False
