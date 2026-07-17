"""Admin quality-check APIs (PRD E8)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.core.deps import DbSession, require_admin
from app.models.user import User
from app.services.qc.service import DEFAULT_LOW_SCORE, LIST_DEFAULT, LIST_MAX, QcService

router = APIRouter(dependencies=[Depends(require_admin)])


@router.get("/summary")
async def qc_summary(db: DbSession, _user: User = Depends(require_admin)) -> dict:
    return await QcService(db).summary()


@router.get("/low-quality")
async def qc_low_quality(
    db: DbSession,
    _user: User = Depends(require_admin),
    threshold: int = Query(default=DEFAULT_LOW_SCORE, ge=0, le=100),
    limit: int = Query(default=LIST_DEFAULT, ge=1, le=LIST_MAX),
) -> dict:
    rows = await QcService(db).low_quality_runs(threshold=threshold, limit=limit)
    return {"threshold": threshold, "count": len(rows), "runs": rows}
