from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.core.deps import CurrentUser, DbSession, require_admin
from app.models.user import User
from app.schemas.knowledge import DraftCreate, DraftOut, GapOut
from app.services.knowledge.draft.service import DraftService
from app.services.knowledge.gap.service import GapService

router = APIRouter(dependencies=[Depends(require_admin)])


@router.get("", response_model=list[GapOut])
async def list_gaps(db: DbSession, _user: User = Depends(require_admin)) -> list[GapOut]:
    rows = await GapService(db).list_open()
    return [GapOut.model_validate(r) for r in rows]


@router.post("/{gap_id}/dismiss", response_model=GapOut)
async def dismiss_gap(gap_id: str, db: DbSession, _user: User = Depends(require_admin)) -> GapOut:
    gap = await GapService(db).dismiss(gap_id)
    if gap is None:
        raise HTTPException(status_code=404, detail="Gap not found")
    return GapOut.model_validate(gap)


@router.post("/{gap_id}/promote", response_model=DraftOut)
async def promote_gap(
    gap_id: str,
    payload: DraftCreate,
    db: DbSession,
    user: CurrentUser,
) -> DraftOut:
    from app.models.knowledge import KnowledgeGap

    gap = await db.get(KnowledgeGap, gap_id)
    if gap is None:
        raise HTTPException(status_code=404, detail="Gap not found")
    draft = await DraftService(db).create(
        title=payload.title or f"FAQ: {gap.question[:80]}",
        content=payload.content,
        created_by=user.id,
        gap_id=gap_id,
    )
    return DraftOut.model_validate(draft)
