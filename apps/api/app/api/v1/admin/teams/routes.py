from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.deps import DbSession, require_admin, require_agent_or_admin
from app.models.user import User
from app.services.team.service import TeamService

router = APIRouter()


class TeamCreate(BaseModel):
    name: str
    description: str = ""
    intent_scope: str = ""


class MemberIn(BaseModel):
    user_id: str


@router.get("")
async def list_teams(
    db: DbSession,
    _user: User = Depends(require_agent_or_admin),
) -> list[dict]:
    svc = TeamService(db)
    rows = await svc.list_teams()
    out: list[dict] = []
    for t in rows:
        members = await svc.list_members(t.id)
        out.append(
            {
                "id": t.id,
                "name": t.name,
                "description": t.description,
                "intent_scope": t.intent_scope,
                "member_ids": [m.user_id for m in members],
                "member_count": len(members),
            }
        )
    return out


@router.post("")
async def create_team(
    body: TeamCreate,
    db: DbSession,
    _user: User = Depends(require_admin),
) -> dict:
    t = await TeamService(db).create_team(
        body.name, description=body.description, intent_scope=body.intent_scope
    )
    return {"id": t.id, "name": t.name, "intent_scope": t.intent_scope}


@router.get("/{team_id}/members")
async def list_members(
    team_id: str,
    db: DbSession,
    _user: User = Depends(require_agent_or_admin),
) -> list[dict]:
    members = await TeamService(db).list_members(team_id)
    return [{"id": m.id, "team_id": m.team_id, "user_id": m.user_id} for m in members]


@router.post("/{team_id}/members")
async def add_member(
    team_id: str,
    body: MemberIn,
    db: DbSession,
    _user: User = Depends(require_admin),
) -> dict:
    m = await TeamService(db).add_member(team_id, body.user_id)
    return {"id": m.id, "team_id": m.team_id, "user_id": m.user_id}


@router.get("/{team_id}/suggest-assignee")
async def suggest_assignee(
    team_id: str,
    db: DbSession,
    _user: User = Depends(require_agent_or_admin),
) -> dict:
    """E3: least open claimed load among team members."""
    uid = await TeamService(db).least_open_member(team_id)
    return {"team_id": team_id, "suggested_user_id": uid, "strategy": "least_open"}
