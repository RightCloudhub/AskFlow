"""Offline notification center: signed webhook + in-memory sink (PRD E2).

Failures never raise into the chat main path — callers should catch or use emit_safe.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from typing import Any

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.middleware.metrics import NOTIFY_TOTAL
from app.models.notify import NotificationLog

# Process-local sink for tests / local offline delivery proof
_SINK: list[dict[str, Any]] = []


def clear_notify_sink() -> None:
    _SINK.clear()


def get_notify_sink() -> list[dict[str, Any]]:
    return list(_SINK)


def sign_payload(secret: str, body: bytes, timestamp: str) -> str:
    msg = timestamp.encode("utf-8") + b"." + body
    return hmac.new(secret.encode("utf-8"), msg, hashlib.sha256).hexdigest()


class NotifyService:
    def __init__(self, db: AsyncSession | None = None, settings: Settings | None = None) -> None:
        self.db = db
        self.settings = settings or get_settings()

    async def emit_safe(self, event: str, payload: dict[str, Any]) -> dict[str, Any] | None:
        try:
            return await self.emit(event, payload)
        except Exception as exc:  # never block main path
            NOTIFY_TOTAL.labels(event=event, status="error").inc()
            if self.db is not None:
                try:
                    log = NotificationLog(
                        event=event,
                        channel="webhook",
                        status="error",
                        target=self.settings.notify_webhook_url or "sink",
                        payload=payload,
                        error=str(exc)[:500],
                    )
                    self.db.add(log)
                    await self.db.flush()
                except Exception:
                    pass
            return None

    async def emit(self, event: str, payload: dict[str, Any]) -> dict[str, Any]:
        envelope = {
            "event": event,
            "ts": int(time.time()),
            "data": payload,
        }
        body = json.dumps(envelope, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        ts = str(envelope["ts"])
        secret = self.settings.notify_webhook_secret or self.settings.secret_key
        signature = sign_payload(secret, body, ts)
        headers = {
            "Content-Type": "application/json",
            "X-AskFlow-Timestamp": ts,
            "X-AskFlow-Signature": signature,
        }

        # Always record to process sink (offline channel for tests)
        record = {
            "event": event,
            "headers": headers,
            "body": envelope,
            "signature": signature,
        }
        _SINK.append(record)

        url = self.settings.notify_webhook_url
        status = "sent_sink"
        err = None
        if url:
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    resp = await client.post(url, content=body, headers=headers)
                if resp.status_code >= 400:
                    status = "http_error"
                    err = f"HTTP {resp.status_code}"
                else:
                    status = "sent_webhook"
            except Exception as exc:
                status = "error"
                err = str(exc)

        if self.db is not None:
            log = NotificationLog(
                event=event,
                channel="webhook" if url else "sink",
                status=status,
                target=url or "memory_sink",
                payload=envelope,
                error=err,
            )
            self.db.add(log)
            await self.db.flush()

        NOTIFY_TOTAL.labels(event=event, status=status).inc()
        return record
