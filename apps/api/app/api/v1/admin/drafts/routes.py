from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.core.deps import CurrentUser, DbSession, require_admin
from app.models.user import User
from app.schemas.knowledge import DraftCreate, DraftOut
from app.services.audit.logger.service import AuditService
from app.services.knowledge.draft.service import DraftService

router = APIRouter(dependencies=[Depends(require_admin)])


@router.get("", response_model=list[DraftOut])
async def list_drafts(
    db: DbSession,
    status: str | None = None,
    _user: User = Depends(require_admin),
) -> list[DraftOut]:
    rows = await DraftService(db).list_drafts(status=status)
    return [DraftOut.model_validate(r) for r in rows]


@router.post("", response_model=DraftOut)
async def create_draft(
    payload: DraftCreate,
    db: DbSession,
    user: CurrentUser,
) -> DraftOut:
    draft = await DraftService(db).create(
        title=payload.title,
        content=payload.content,
        created_by=user.id,
        gap_id=payload.gap_id,
    )
    return DraftOut.model_validate(draft)


@router.post("/{draft_id}/approve", response_model=DraftOut)
async def approve_draft(
    draft_id: str,
    db: DbSession,
    user: CurrentUser,
) -> DraftOut:
    try:
        draft = await DraftService(db).approve(draft_id, user.id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await AuditService(db).log(
        action="draft.approve",
        resource_type="draft",
        resource_id=draft_id,
        actor_id=user.id,
        detail={"document_id": draft.document_id},
    )
    return DraftOut.model_validate(draft)


@router.post("/{draft_id}/reject", response_model=DraftOut)
async def reject_draft(
    draft_id: str,
    db: DbSession,
    user: CurrentUser,
) -> DraftOut:
    try:
        draft = await DraftService(db).reject(draft_id, user.id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return DraftOut.model_validate(draft)
