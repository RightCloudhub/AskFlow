"""Audit logger — same-transaction best effort (PRD §4.11)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog
from app.services.audit.masking.mask import mask_detail


class AuditService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def log(
        self,
        *,
        action: str,
        resource_type: str,
        resource_id: str | None = None,
        actor_id: str | None = None,
        detail: dict[str, Any] | None = None,
        ip: str | None = None,
        trace_id: str | None = None,
    ) -> AuditLog:
        row = AuditLog(
            actor_id=actor_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            detail=mask_detail(detail),
            ip=ip,
            trace_id=trace_id,
        )
        self.db.add(row)
        await self.db.flush()
        await self.db.refresh(row)
        return row

    async def list_logs(
        self,
        *,
        action: str | None = None,
        limit: int = 100,
    ) -> list[AuditLog]:
        stmt = select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit)
        if action:
            stmt = stmt.where(AuditLog.action == action)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
