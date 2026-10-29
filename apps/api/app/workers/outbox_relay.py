"""Outbox relay loop: publish events committed with their state change (arch §4.5)."""

import asyncio
import logging

from sqlalchemy import text

from app.core import database
from app.services.outbox.relay import publish_event
from app.services.outbox.settings import OutboxSettings
from app.services.outbox.store import mark_published, pending, record_failure

logger = logging.getLogger(__name__)


async def run_once(settings: OutboxSettings | None = None) -> dict:
    settings = settings or OutboxSettings()
    published = 0
    attempted = []
    for _ in range(settings.batch):
        async with database.SessionLocal() as db:
            if db.bind.dialect.name == "sqlite":
                await db.execute(text("BEGIN IMMEDIATE"))
            events = await pending(db, limit=1, max_attempts=settings.max_attempts, excluded=attempted)
            if not events:
                break
            event = events[0]
            attempted.append(event.id)
            if await _publish_one(db, event):
                published += 1
            await db.commit()
    return {"published": published}


async def _publish_one(db, event) -> bool:
    try:
        async with db.begin_nested():
            await publish_event(db, event)
            await mark_published(db, event)
        return True
    except Exception as exc:  # noqa: BLE001 - per-item failure is recorded, not re-raised
        error = type(exc).__name__
        await record_failure(db, event, error)
        logger.warning("outbox publish failed id=%s error_type=%s", event.id, error)
        return False


async def periodic_loop(settings: OutboxSettings | None = None) -> None:
    settings = settings or OutboxSettings()
    while True:
        try:
            await run_once(settings)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("outbox relay cycle failed")
        await asyncio.sleep(settings.poll_seconds)
