"""Handoff inbox for agents (PRD §4.7)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentUser, DbSession, require_agent_or_admin
from app.models.handoff import HandoffSession
from app.models.user import User
from app.schemas.chat import MessageOut
from app.schemas.handoff import HandoffOut, StaffReplyRequest
from app.services.handoff.service import HandoffService
from app.services.handoff.staff_ops import HandoffStaffOps

router = APIRouter(dependencies=[Depends(require_agent_or_admin)])


async def _with_names(db: AsyncSession, rows: list[HandoffSession]) -> list[HandoffOut]:
    """Customer and claimant usernames for the inbox, resolved in one query."""
    ids = {r.user_id for r in rows} | {r.claimed_by for r in rows if r.claimed_by}
    names: dict[str, str] = {}
    if ids:
        result = await db.execute(select(User.id, User.username).where(User.id.in_(ids)))
        names = dict(result.tuples().all())
    out = []
    for r in rows:
        item = HandoffOut.model_validate(r)
        item.user_name = names.get(r.user_id)
        item.claimed_by_name = names.get(r.claimed_by) if r.claimed_by else None
        out.append(item)
    return out


@router.get("", response_model=list[HandoffOut])
async def list_handoffs(
    db: DbSession,
    user: User = Depends(require_agent_or_admin),
) -> list[HandoffOut]:
    rows = await HandoffService(db).list_queue(agent_id=user.id, agent_role=user.role)
    return await _with_names(db, rows)


@router.post("/{handoff_id}/claim", response_model=HandoffOut)
async def claim_handoff(
    handoff_id: str,
    *,
    user: CurrentUser,
    db: DbSession,
) -> HandoffOut:
    session = await HandoffService(db).claim(handoff_id, user.id, agent_role=user.role)
    return (await _with_names(db, [session]))[0]


@router.post("/{handoff_id}/return", response_model=HandoffOut)
async def return_handoff(
    handoff_id: str,
    *,
    user: CurrentUser,
    db: DbSession,
) -> HandoffOut:
    session = await HandoffService(db).return_to_ai(handoff_id, user.id)
    return HandoffOut.model_validate(session)


@router.get("/{handoff_id}/messages", response_model=list[MessageOut])
async def list_handoff_messages(
    handoff_id: str,
    *,
    user: CurrentUser,
    db: DbSession,
) -> list[MessageOut]:
    rows = await HandoffStaffOps(db).list_messages(handoff_id, user.id, agent_role=user.role)
    return [MessageOut.model_validate(r) for r in rows]


@router.post("/{handoff_id}/reply", response_model=MessageOut)
async def staff_reply(
    handoff_id: str,
    body: StaffReplyRequest,
    *,
    user: CurrentUser,
    db: DbSession,
) -> MessageOut:
    msg = await HandoffStaffOps(db).staff_reply(
        handoff_id,
        user.id,
        body.content,
        agent_role=user.role,
    )
    return MessageOut.model_validate(msg)
