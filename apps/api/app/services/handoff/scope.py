"""Team intent-scope filtering for handoff queue (M4)."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.handoff import HandoffSession


async def filter_queue_by_team(
    db: AsyncSession,
    rows: list[HandoffSession],
    *,
    agent_id: str,
) -> list[HandoffSession]:
    """Apply team intent_scope rules to queued handoffs."""
    from app.services.team.service import TeamService

    team_svc = TeamService(db)
    team_ids = await team_svc.user_team_ids(agent_id)
    if not team_ids:
        return []

    teams = await team_svc.list_teams()
    member_teams = [t for t in teams if t.id in team_ids]
    if _has_catch_all(member_teams):
        return rows

    scopes = await team_svc.team_intent_scopes(agent_id)
    if not scopes:
        return []
    return [h for h in rows if (h.intent or "handoff") in scopes]


def _has_catch_all(member_teams: list) -> bool:
    return any(not (t.intent_scope or "").strip() for t in member_teams)


def merge_inbox(
    queued: list[HandoffSession],
    claimed: list[HandoffSession],
) -> list[HandoffSession]:
    """Queued first (FIFO), then mine claimed; dedupe by id."""
    seen: set[str] = set()
    out: list[HandoffSession] = []
    for h in queued + claimed:
        if h.id in seen:
            continue
        seen.add(h.id)
        out.append(h)
    return out
