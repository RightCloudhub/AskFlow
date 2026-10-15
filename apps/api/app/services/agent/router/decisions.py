"""Persist one RouterDecision per turn so misroutes can be replayed (arch §4.3 / §10.2)."""

from app.models.router_decision import RouterDecisionRecord
from app.services.agent.router.settings import RouterSettings


async def record_decision(
    db,
    *,
    turn_id: str,
    conversation_id: str,
    route: str,
    goal_key: str | None = None,
    goal_version: int | None = None,
    confidence: float = 0.0,
    method: str = "rule",
    slots: dict | None = None,
    missing_slots: list | None = None,
    identity_requirement: dict | None = None,
    active_task_relation: str | None = None,
    latency_ms: int = 0,
) -> RouterDecisionRecord:
    row = RouterDecisionRecord(
        turn_id=turn_id,
        conversation_id=conversation_id,
        route=route,
        goal_key=goal_key,
        goal_version=goal_version,
        confidence=confidence,
        method=method,
        slots=slots or {},
        missing_slots=missing_slots or [],
        identity_requirement=identity_requirement,
        active_task_relation=active_task_relation,
        router_version=RouterSettings().version,
        latency_ms=latency_ms,
    )
    db.add(row)
    await db.flush()
    return row
