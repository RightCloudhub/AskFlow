"""Channel inbox relay: process deduplicated inbound messages in per-session order (arch §9.1)."""

import asyncio
import logging

from app.core import database
from app.core.config import get_settings
from app.services.channels.canonical import CanonicalMessage
from app.services.channels.inbox import claim_batch, mark_published, record_failure
from app.services.channels.settings import ChannelSettings
from app.services.channels.turn import process_canonical

logger = logging.getLogger(__name__)


async def run_once(settings: ChannelSettings | None = None) -> dict:
    settings = settings or ChannelSettings()
    processed = 0
    async with database.SessionLocal() as db:
        rows = await claim_batch(
            db, limit=settings.inbox_batch, max_attempts=settings.inbox_max_attempts
        )
        for row in rows:
            if await _process_row(db, row):
                processed += 1
            await db.commit()
    return {"processed": processed}


async def _process_row(db, row) -> bool:
    try:
        message = CanonicalMessage.from_payload(row.payload)
        await process_canonical(db, message, get_settings())
        await mark_published(db, row)
        return True
    except Exception as exc:  # noqa: BLE001 - per-item failure is recorded, not re-raised
        await record_failure(db, row, str(exc))
        logger.warning("channel inbox row failed id=%s error=%s", row.id, exc)
        return False


async def periodic_loop(settings: ChannelSettings | None = None) -> None:
    settings = settings or ChannelSettings()
    while True:
        try:
            await run_once(settings)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("channel inbox relay cycle failed")
        await asyncio.sleep(settings.inbox_poll_seconds)
