"""Outbox relay loop: publish events committed with their state change (arch §4.5)."""

import asyncio
import logging

from app.core import database
from app.services.outbox.relay import publish_event
from app.services.outbox.settings import OutboxSettings
from app.services.outbox.store import mark_published, pending, record_failure

logger = logging.getLogger(__name__)


async def run_once(settings: OutboxSettings | None = None) -> dict:
    settings = settings or OutboxSettings()
    published = 0
    async with database.SessionLocal() as db:
        events = await pending(db, limit=settings.batch, max_attempts=settings.max_attempts)
        for event in events:
            if await _publish_one(db, event):
                published += 1
            await db.commit()
    return {"published": published}


async def _publish_one(db, event) -> bool:
    try:
        await publish_event(db, event)
        await mark_published(db, event)
        return True
    except Exception as exc:  # noqa: BLE001 - per-item failure is recorded, not re-raised
        await record_failure(db, event, str(exc))
        logger.warning("outbox publish failed id=%s error=%s", event.id, exc)
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
