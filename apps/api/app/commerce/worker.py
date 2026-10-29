"""Identical job code runs in-process or as a separate replica-safe worker."""

import asyncio
import logging
from datetime import UTC, datetime

from sqlalchemy import delete, text

from app.commerce.core.leases import claim, release
from app.commerce.core.models import IdempotencyRecord
from app.commerce.job_handlers import dispatch
from app.commerce.job_registry import JOBS, active, pending_ids
from app.core import database
from app.core.config import get_settings

logger = logging.getLogger("askflow.mall.worker")
LEASE_KEY = "mall:maintenance"


async def run_once():
    counts = {}
    for job in JOBS:
        if not active(job):
            continue
        async with database.SessionLocal() as db:
            identifiers = await pending_ids(db, job)
        counts[job.name] = 0
        for resource_id in identifiers:
            counts[job.name] += await run_item(job, resource_id)
    await cleanup()
    await daily_finance()
    return counts


async def daily_finance():
    from app.commerce.core.services import enabled
    from app.commerce.wallet.schedule import daily

    if not enabled("wallet"):
        return
    async with database.SessionLocal() as db:
        if db.bind.dialect.name == "sqlite":
            await db.execute(text("BEGIN IMMEDIATE"))
        await daily(db)
        await db.commit()


async def run_item(job, resource_id: str):
    try:
        async with database.SessionLocal() as db:
            if db.bind.dialect.name == "sqlite":
                await db.execute(text("BEGIN IMMEDIATE"))
            key = "mall:" + job.name + ":" + resource_id
            owner = await claim(db, key)
            if owner is None:
                await db.rollback()
                return 0
            await dispatch(db, job, resource_id=resource_id)
            await release(db, key, owner)
            await db.commit()
            return 1
    except Exception as exc:
        logger.warning("mall job failed job=%s error_type=%s", job.name, type(exc).__name__)
        return 0


async def cleanup():
    from app.commerce.observability import sample

    async with database.SessionLocal() as db:
        if db.bind.dialect.name == "sqlite":
            await db.execute(text("BEGIN IMMEDIATE"))
        owner = await claim(db, LEASE_KEY)
        if owner is None:
            await db.rollback()
            return {"claimed": False}
        await db.execute(delete(IdempotencyRecord).where(IdempotencyRecord.expires_at < datetime.now(UTC),
            IdempotencyRecord.status == "completed"))
        await sample(db)
        await release(db, LEASE_KEY, owner)
        await db.commit()


async def periodic_loop():
    while True:
        try:
            await run_once()
            await streams()
        except Exception as exc:
            logger.warning("mall jobs failed error_type=%s", type(exc).__name__)
        await asyncio.sleep(get_settings().mall_worker_poll_seconds)


async def streams():
    from app.commerce.core.services import enabled
    from app.commerce.inventory.flash_reconcile import reconcile
    from app.commerce.stream_worker import poll

    if not enabled("inventory") or not enabled("order"):
        return
    await poll()
    async with database.SessionLocal() as db:
        await reconcile(db)


async def main():
    from app.core.background import _legacy_loops
    from app.core.schema import prepare_schema
    from app.plugins.loader import boot_plugins, load_plugins, shutdown_plugins
    from importlib import import_module

    settings = get_settings()
    settings.assert_startup_safe()
    ctx = load_plugins(settings)
    await prepare_schema(settings)
    await boot_plugins(ctx)
    loops = [getattr(import_module(module), method)(*args)
             for _name, module, method, args in _legacy_loops(settings, ctx)]
    try:
        await asyncio.gather(periodic_loop(), *loops)
    finally:
        await shutdown_plugins(ctx)


if __name__ == "__main__":
    asyncio.run(main())
