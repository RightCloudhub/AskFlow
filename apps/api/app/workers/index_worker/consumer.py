"""Index worker consumer: dequeue → chunk → embed → upsert (PRD §4.8)."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.core import database as dbmod
from app.core.config import Settings, get_settings
from app.middleware.metrics import INDEX_JOBS_TOTAL
from app.workers.index_worker.queue import IndexJob, IndexQueue, get_index_queue

logger = logging.getLogger("askflow.index_worker")

DEFAULT_POLL_SEC = 1.0
MIN_POLL_SEC = 0.2
ERROR_MSG_MAX = 200


async def process_job(job: IndexJob) -> dict[str, Any]:
    """Run one index job inside a DB session."""
    from app.services.knowledge.indexer.service import IndexerService
    from app.services.knowledge.storage.local import LocalObjectStorage

    async with dbmod.SessionLocal() as db:
        try:
            doc = await IndexerService(db, LocalObjectStorage()).index_document(job.document_id)
            await db.commit()
            INDEX_JOBS_TOTAL.labels(status="ok").inc()
            return {
                "document_id": doc.id,
                "status": doc.status,
                "chunk_count": doc.chunk_count,
                "generation": doc.generation,
            }
        except Exception as exc:
            await db.rollback()
            INDEX_JOBS_TOTAL.labels(status="error").inc()
            logger.exception("index job failed document_id=%s", job.document_id)
            return {"document_id": job.document_id, "error": str(exc)[:ERROR_MSG_MAX]}


async def consume_once(queue: IndexQueue | None = None) -> dict[str, Any] | None:
    queue = queue or get_index_queue()
    job = await queue.dequeue()
    if job is None:
        return None
    return await process_job(job)


async def consumer_loop(settings: Settings | None = None) -> None:
    settings = settings or get_settings()
    queue = get_index_queue(settings)
    poll = max(MIN_POLL_SEC, float(settings.index_worker_poll_seconds))
    logger.info("index worker loop started poll_sec=%s", poll)
    while True:
        try:
            result = await consume_once(queue)
            if result is not None:
                logger.info("index worker ok %s", result)
            else:
                await asyncio.sleep(poll)
        except asyncio.CancelledError:
            logger.info("index worker loop cancelled")
            raise
        except Exception:
            logger.exception("index worker cycle failed")
            await asyncio.sleep(poll)
