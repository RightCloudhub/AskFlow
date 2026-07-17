from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends

from app.core.config import get_settings
from app.core.deps import DbSession, require_admin, require_agent_or_admin
from app.models.user import User
from app.services.handoff.timeout import HandoffTimeoutSweeper

router = APIRouter()


@router.get("/health")
async def admin_health(
    db: DbSession,
    _user: User = Depends(require_agent_or_admin),
) -> dict:
    from app.api.v1.health.routes import health

    body = await health()
    return body.model_dump()


@router.post("/handoff-sweep")
async def run_handoff_sweep(
    db: DbSession,
    _user: User = Depends(require_admin),
) -> dict:
    outcomes = await HandoffTimeoutSweeper(db).sweep()
    return {"swept": len(outcomes), "outcomes": outcomes}


@router.post("/handoff-sweep/force-expire")
async def force_expire_for_test(
    db: DbSession,
    _user: User = Depends(require_admin),
) -> dict:
    """Test helper: backdate queued handoffs past timeout then sweep."""
    from sqlalchemy import select

    from app.models.enums import HandoffStatus
    from app.models.handoff import HandoffSession

    settings = get_settings()
    result = await db.execute(
        select(HandoffSession).where(HandoffSession.status == HandoffStatus.QUEUED.value)
    )
    sessions = list(result.scalars().all())
    past = datetime.now(UTC) - timedelta(seconds=settings.handoff_timeout_seconds + 10)
    for s in sessions:
        s.created_at = past
    await db.flush()
    outcomes = await HandoffTimeoutSweeper(db).sweep()
    return {"backdated": len(sessions), "swept": len(outcomes), "outcomes": outcomes}
