"""Index job queue: in-process asyncio.Queue + optional Redis list."""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import asdict, dataclass
from typing import Any

from app.core.config import Settings, get_settings

logger = logging.getLogger("askflow.index_queue")

REDIS_KEY_DEFAULT = "askflow:index_jobs"
QUEUE_GET_TIMEOUT_SEC = 1.0


@dataclass
class IndexJob:
    document_id: str
    generation_hint: int | None = None

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)

    @classmethod
    def from_json(cls, raw: str) -> IndexJob:
        data = json.loads(raw)
        return cls(
            document_id=str(data["document_id"]),
            generation_hint=data.get("generation_hint"),
        )


class IndexQueue:
    """Dual backend: always local asyncio queue; Redis when REDIS_URL set."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._local: asyncio.Queue[IndexJob] = asyncio.Queue()
        self._redis_key = self.settings.index_queue_key

    async def enqueue(self, job: IndexJob) -> None:
        await self._local.put(job)
        await self._redis_push(job)
        logger.info("index job enqueued document_id=%s", job.document_id)

    async def dequeue(self, timeout: float = QUEUE_GET_TIMEOUT_SEC) -> IndexJob | None:
        job = await self._redis_pop()
        if job is not None:
            return job
        try:
            return await asyncio.wait_for(self._local.get(), timeout=timeout)
        except asyncio.TimeoutError:
            return None

    async def _redis_push(self, job: IndexJob) -> None:
        url = self.settings.redis_url
        if not url:
            return
        try:
            import redis.asyncio as redis

            client = redis.from_url(url)
            await client.rpush(self._redis_key, job.to_json())
            await client.aclose()
        except Exception:
            logger.exception("redis enqueue failed; local queue retained")

    async def _redis_pop(self) -> IndexJob | None:
        url = self.settings.redis_url
        if not url:
            return None
        try:
            import redis.asyncio as redis

            client = redis.from_url(url)
            raw = await client.lpop(self._redis_key)
            await client.aclose()
            if raw is None:
                return None
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8")
            return IndexJob.from_json(str(raw))
        except Exception:
            logger.exception("redis dequeue failed")
            return None

    def qsize_local(self) -> int:
        return self._local.qsize()


_queue: IndexQueue | None = None


def get_index_queue(settings: Settings | None = None) -> IndexQueue:
    global _queue
    if _queue is None:
        _queue = IndexQueue(settings or get_settings())
    return _queue


def reset_index_queue() -> None:
    global _queue
    _queue = None


def job_payload(document_id: str, **extra: Any) -> IndexJob:
    return IndexJob(document_id=document_id, generation_hint=extra.get("generation_hint"))
