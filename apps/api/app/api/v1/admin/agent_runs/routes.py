"""Admin Agent run list/detail (PRD S-08)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.deps import DbSession, require_admin
from app.models.user import User
from app.services.agent.run_store import DEFAULT_LIST_LIMIT, MAX_LIST_LIMIT, AgentRunStore

router = APIRouter(dependencies=[Depends(require_admin)])
HTTP_NOT_FOUND = 404


def _run_out(row, cost: dict | None = None) -> dict:
    body = {
        "id": row.id,
        "run_id": row.run_id,
        "conversation_id": row.conversation_id,
        "user_id": row.user_id,
        "route": row.route,
        "intent": row.intent,
        "refused": row.refused,
        "flags": row.flags or [],
        "steps": row.steps or [],
        "cost_summary": row.cost_summary or {},
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }
    if cost is not None:
        body["cost"] = cost
    return body


@router.get("")
async def list_agent_runs(
    db: DbSession,
    _user: User = Depends(require_admin),
    limit: int = Query(default=DEFAULT_LIST_LIMIT, ge=1, le=MAX_LIST_LIMIT),
) -> list[dict]:
    rows = await AgentRunStore(db).list_recent(limit=limit)
    return [_run_out(r) for r in rows]


@router.get("/{run_id}")
async def get_agent_run(
    run_id: str,
    db: DbSession,
    _user: User = Depends(require_admin),
) -> dict:
    store = AgentRunStore(db)
    row = await store.get_by_run_id(run_id)
    if row is None:
        raise HTTPException(status_code=HTTP_NOT_FOUND, detail="run_not_found")
    cost = await store.cost_for_run(run_id)
    return _run_out(row, cost=cost)
