"""Versioned customer cancellation and verified staff takeover."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update

from app.models.handoff import HandoffSession
from app.services.agent.identity import customer_scope
from app.services.agent.service.contracts import Record, Scope, Task, TaskTransition
from app.services.agent.service.store import TaskConflict, TaskStore

CONTROL_REVIEW_SECONDS = 60
CONTROLLABLE_STATES = frozenset({"active", "waiting_customer", "waiting_external"})


class InvalidTransition(ValueError):
    """Task is no longer in a state that permits the requested transition."""


class HandoffAcceptance(Record):
    task_id: str
    handoff_id: str
    actor_id: str
    expected_version: int


def check_control(task: Task, expected_version: int) -> None:
    if task.version != expected_version:
        raise TaskConflict("Stale task checkpoint")
    if task.status not in CONTROLLABLE_STATES:
        raise InvalidTransition("Task cannot transition from its current state")


def unsettled(task: Task) -> bool:
    return any(entry.status in {"running", "unknown"} for entry in task.ledger)


def transition(task: Task, *, status: str, actor: str, reason: str) -> None:
    task.transitions.append(
        TaskTransition(previous=task.status, current=status, actor_id=actor, reason=reason)
    )
    task.status = status
    task.wake_condition, task.review_at = None, None
    if unsettled(task):
        task.wake_condition = "owner_review:unsettled_operations"
        task.review_at = datetime.now(UTC) + timedelta(seconds=CONTROL_REVIEW_SECONDS)


async def cancel_task(
    store: TaskStore, task_id: str, *, scope: Scope, expected_version: int, reason: str
) -> Task:
    task = await store.load(task_id, scope)
    check_control(task, expected_version)
    transition(task, status="closed_unresolved", actor=scope.customer_id, reason=reason)
    await store.save(task)
    return task


async def accept_handoff(store: TaskStore, request: HandoffAcceptance) -> Task:
    async with store.sessions.begin() as db:
        # This conditional update locks the claim on SQLite as well as PostgreSQL.
        claimed = await db.execute(
            update(HandoffSession)
            .where(
                HandoffSession.id == request.handoff_id,
                HandoffSession.claimed_by == request.actor_id,
                HandoffSession.status == "claimed",
            )
            .values(status="claimed")
        )
        if claimed.rowcount != 1:
            raise LookupError("Claimed handoff not found")
        handoff = await db.scalar(
            select(HandoffSession).where(HandoffSession.id == request.handoff_id)
        )
        task = await store.load_in_transaction(
            db, request.task_id, scope=customer_scope(handoff.user_id)
        )
        if task.conversation_id != handoff.conversation_id:
            raise LookupError("Task does not belong to this handoff")
        check_control(task, request.expected_version)
        transition(
            task, status="handed_off", actor=request.actor_id, reason=f"handoff:{handoff.id}"
        )
        task.owner = request.actor_id
        task.review_at = datetime.now(UTC) + timedelta(seconds=CONTROL_REVIEW_SECONDS)
        task.wake_condition = task.wake_condition or f"handoff_review:{handoff.id}"
        await store.write_checkpoint(db, task)
    task.version += 1
    return task
