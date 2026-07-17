from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from app.core.deps import DbSession, require_admin
from app.models.user import User
from app.schemas.knowledge import AuditLogOut
from app.services.audit.logger.service import AuditService
from app.services.audit.siem import (
    DEFAULT_EXPORT_LIMIT,
    MAX_EXPORT_LIMIT,
    SiemExportService,
)

router = APIRouter(dependencies=[Depends(require_admin)])
LIST_CAP = 500


class SiemPushBody(BaseModel):
    action: str | None = None
    limit: int = Field(default=DEFAULT_EXPORT_LIMIT, ge=1, le=MAX_EXPORT_LIMIT)
    push: bool = True


@router.get("", response_model=list[AuditLogOut])
async def list_audit_logs(
    db: DbSession,
    action: str | None = None,
    limit: int = 100,
    _user: User = Depends(require_admin),
) -> list[AuditLogOut]:
    rows = await AuditService(db).list_logs(action=action, limit=min(limit, LIST_CAP))
    return [AuditLogOut.model_validate(r) for r in rows]


@router.get("/export-siem")
async def export_siem(
    db: DbSession,
    _user: User = Depends(require_admin),
    action: str | None = None,
    limit: int = Query(default=DEFAULT_EXPORT_LIMIT, ge=1, le=MAX_EXPORT_LIMIT),
) -> dict:
    """JSON batch for SIEM collectors (PRD E9)."""
    events = await SiemExportService(db).export_events(action=action, limit=limit)
    return {"count": len(events), "events": events}


@router.post("/export-siem")
async def push_siem(
    body: SiemPushBody,
    db: DbSession,
    _user: User = Depends(require_admin),
) -> dict:
    """Export audit events and optionally POST to SIEM_WEBHOOK_URL."""
    svc = SiemExportService(db)
    events = await svc.export_events(action=body.action, limit=body.limit)
    result: dict = {"count": len(events), "events": events if not body.push else None}
    if body.push:
        result["delivery"] = await svc.push_to_webhook(events)
    return result
