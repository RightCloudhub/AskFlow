"""SIEM export / push of audit logs (PRD E9 skeleton)."""

from __future__ import annotations

import json
import time
from typing import Any

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.services.audit.logger.service import AuditService

HTTP_TIMEOUT_SEC = 8.0
DEFAULT_EXPORT_LIMIT = 100
MAX_EXPORT_LIMIT = 500


def audit_to_siem_event(row: Any) -> dict[str, Any]:
    return {
        "ts": int(time.time()),
        "source": "askflow",
        "event_type": "audit",
        "action": row.action,
        "resource_type": row.resource_type,
        "resource_id": row.resource_id,
        "actor_id": row.actor_id,
        "detail": row.detail or {},
        "ip": row.ip,
        "trace_id": row.trace_id,
        "id": row.id,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


class SiemExportService:
    def __init__(self, db: AsyncSession, settings: Settings | None = None) -> None:
        self.db = db
        self.settings = settings or get_settings()

    async def export_events(
        self,
        *,
        action: str | None = None,
        limit: int = DEFAULT_EXPORT_LIMIT,
    ) -> list[dict[str, Any]]:
        cap = max(1, min(limit, MAX_EXPORT_LIMIT))
        rows = await AuditService(self.db).list_logs(action=action, limit=cap)
        return [audit_to_siem_event(r) for r in rows]

    async def push_to_webhook(
        self,
        events: list[dict[str, Any]],
        *,
        url: str | None = None,
    ) -> dict[str, Any]:
        target = url or self.settings.siem_webhook_url
        if not target:
            return {"status": "skipped", "reason": "siem_webhook_not_configured", "count": len(events)}
        body = json.dumps({"events": events}, ensure_ascii=False).encode("utf-8")
        try:
            async with httpx.AsyncClient(timeout=HTTP_TIMEOUT_SEC) as client:
                resp = await client.post(
                    target,
                    content=body,
                    headers={"Content-Type": "application/json", "X-AskFlow-Source": "siem-export"},
                )
            if resp.status_code >= 400:
                return {
                    "status": "http_error",
                    "http_status": resp.status_code,
                    "count": len(events),
                }
            return {"status": "sent", "http_status": resp.status_code, "count": len(events)}
        except Exception as exc:
            return {"status": "error", "error": str(exc)[:300], "count": len(events)}
