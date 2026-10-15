"""Outbound delivery: render, split, retry with backoff, rate limit, delivery log (arch §4.1)."""

import asyncio
import time

from app.models.notify import NotificationLog
from app.services.outbound.render import render_parts
from app.services.outbound.senders import get_sender
from app.services.outbound.settings import OutboundSettings

EVENT_AGENT_PUSH = "agent.push"
STATUS_SENT = "sent"
STATUS_LOCAL_ONLY = "local_only"
STATUS_RATE_LIMITED = "rate_limited"
STATUS_FAILED = "failed"
LOG_TEXT_LIMIT = 500
ERROR_TEXT_LIMIT = 80
SECONDS_PER_MINUTE = 60.0


class TokenBucket:
    def __init__(self, rate_per_minute: int) -> None:
        self.capacity = float(rate_per_minute)
        self.tokens = self.capacity
        self.rate = rate_per_minute / SECONDS_PER_MINUTE
        self.updated = time.monotonic()

    def allow(self) -> bool:
        now = time.monotonic()
        self.tokens = min(self.capacity, self.tokens + (now - self.updated) * self.rate)
        self.updated = now
        if self.tokens < 1:
            return False
        self.tokens -= 1
        return True


_BUCKETS: dict[str, TokenBucket] = {}


def _bucket(channel: str, settings: OutboundSettings) -> TokenBucket:
    return _BUCKETS.setdefault(channel, TokenBucket(settings.rate_per_minute))


class OutboundDelivery:
    def __init__(self, settings: OutboundSettings | None = None, sender_resolver=None) -> None:
        self.settings = settings or OutboundSettings()
        self._resolve = sender_resolver or get_sender

    async def deliver(
        self, db, *, channel: str, target: str, text: str, event_type: str = EVENT_AGENT_PUSH
    ) -> str:
        sender = self._resolve(channel)
        if sender is None:
            await self._log(
                db, event_type=event_type, channel=channel, status=STATUS_LOCAL_ONLY,
                target=target, text=text,
            )
            return STATUS_LOCAL_ONLY
        status = STATUS_FAILED
        for part in render_parts(text, channel=channel, settings=self.settings):
            if not _bucket(channel, self.settings).allow():
                status = STATUS_RATE_LIMITED
                break
            status = await self._send_with_retry(sender, target=target, text=part)
            if status != STATUS_SENT:
                break
        await self._log(
            db, event_type=event_type, channel=channel, status=status, target=target, text=text
        )
        return status

    async def _send_with_retry(self, sender, *, target: str, text: str) -> str:
        status = STATUS_FAILED
        for attempt in range(self.settings.max_attempts):
            try:
                status = await sender(target=target, text=text)
            except Exception as exc:
                status = f"error:{str(exc)[:ERROR_TEXT_LIMIT]}"
            if status == STATUS_SENT:
                return status
            if attempt + 1 < self.settings.max_attempts:
                await asyncio.sleep(self.settings.retry_base_seconds * (2**attempt))
        return status

    async def _log(self, db, *, event_type: str, channel: str, status: str, target: str, text: str) -> None:
        db.add(
            NotificationLog(
                event=event_type,
                channel=channel,
                status=status,
                target=target,
                payload={"text": text[:LOG_TEXT_LIMIT]},
            )
        )
        await db.flush()
