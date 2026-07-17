"""Handoff inbox for agents (PRD §4.7)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.deps import CurrentUser, DbSession, require_agent_or_admin
from app.models.user import User
from app.schemas.handoff import HandoffOut
from app.services.handoff.service import HandoffService

router = APIRouter(dependencies=[Depends(require_agent_or_admin)])


@router.get("", response_model=list[HandoffOut])
async def list_handoffs(
    db: DbSession,
    user: User = Depends(require_agent_or_admin),
) -> list[HandoffOut]:
    rows = await HandoffService(db).list_queue(agent_id=user.id, agent_role=user.role)
    return [HandoffOut.model_validate(r) for r in rows]


@router.post("/{handoff_id}/claim", response_model=HandoffOut)
async def claim_handoff(
    handoff_id: str,
    user: CurrentUser,
    db: DbSession,
) -> HandoffOut:
    # role checked by router dependency
    session = await HandoffService(db).claim(handoff_id, user.id)
    return HandoffOut.model_validate(session)


@router.post("/{handoff_id}/return", response_model=HandoffOut)
async def return_handoff(
    handoff_id: str,
    user: CurrentUser,
    db: DbSession,
) -> HandoffOut:
    session = await HandoffService(db).return_to_ai(handoff_id, user.id)
    return HandoffOut.model_validate(session)
