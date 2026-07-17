"""Admin notify test-emit + recent logs (pilot operability)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.core.deps import DbSession, require_admin
from app.models.notify import NotificationLog
from app.models.user import User
from app.services.notify.service import NotifyService

router = APIRouter(dependencies=[Depends(require_admin)])
DEFAULT_LOG_LIMIT = 20
MAX_LOG_LIMIT = 100


class TestEmitBody(BaseModel):
    event: str = "pilot.test"
    payload: dict[str, Any] = Field(default_factory=dict)


@router.post("/test-emit")
async def test_emit(
    body: TestEmitBody,
    db: DbSession,
    _user: User = Depends(require_admin),
) -> dict:
    """Exercise signed webhook / sink without touching chat path."""
    rec = await NotifyService(db).emit_safe(body.event, body.payload or {"source": "admin"})
    return {
        "ok": rec is not None,
        "signature": (rec or {}).get("signature"),
        "event": body.event,
        "headers": (rec or {}).get("headers"),
    }


@router.get("/logs")
async def list_notify_logs(
    db: DbSession,
    _user: User = Depends(require_admin),
    limit: int = Query(default=DEFAULT_LOG_LIMIT, ge=1, le=MAX_LOG_LIMIT),
) -> list[dict]:
    result = await db.execute(
        select(NotificationLog).order_by(NotificationLog.created_at.desc()).limit(limit)
    )
    rows = list(result.scalars().all())
    return [
        {
            "id": r.id,
            "event": r.event,
            "channel": r.channel,
            "status": r.status,
            "target": r.target,
            "error": r.error,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]
