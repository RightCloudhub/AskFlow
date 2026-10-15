"""Conversation-scoped task operations executed inside the chat transaction (arch §9.4)."""

from datetime import UTC, datetime

from sqlalchemy import select, update

from app.models.service_dispatch import ServiceDispatch
from app.models.service_task import ServiceTask
from app.services.agent.identity import customer_scope
from app.services.agent.service.contracts import ConfirmationGrant, Task
from app.services.agent.service.control import transition
from app.services.agent.service.store import TaskConflict

OPEN_STATUSES = frozenset({"active", "waiting_customer", "waiting_external", "handed_off"})
CONTROLLABLE_STATUSES = frozenset({"active", "waiting_customer", "waiting_external"})


async def open_tasks(db, conversation, *, limit: int) -> list[Task]:
    scope = customer_scope(conversation.user_id)
    rows = await db.scalars(
        select(ServiceTask)
        .where(
            ServiceTask.organization_id == scope.organization_id,
            ServiceTask.customer_id == scope.customer_id,
        )
        .order_by(ServiceTask.created_at.desc())
        .limit(limit)
    )
    tasks = [Task.model_validate(row.checkpoint) for row in rows]
    return [
        task
        for task in tasks
        if task.conversation_id == conversation.id and task.status in OPEN_STATUSES
    ]


async def cancel_open_task(db, task: Task) -> Task:
    transition(task, status="closed_unresolved", actor="customer", reason="customer_cancel")
    await _save(db, task)
    await _dispatch_due(db, task.task_id, due_at=None)
    return task


async def resume_task(
    db, task: Task, *, actor: str = "customer", reason: str = "customer_reply"
) -> Task:
    transition(task, status="active", actor=actor, reason=reason)
    await _save(db, task)
    await _dispatch_due(db, task.task_id, due_at=datetime.now(UTC))
    return task


async def resolve_task(db, task: Task, *, actor: str, reason: str) -> Task:
    transition(task, status="resolved", actor=actor, reason=reason)
    await _save(db, task)
    await _dispatch_due(db, task.task_id, due_at=None)
    return task


async def grant_confirmation(db, task: Task) -> Task:
    pending = task.pending_confirmation
    if pending is None:
        return task
    task.confirmations.append(
        ConfirmationGrant(
            capability=pending.capability, args_hash=pending.args_hash, nonce=pending.nonce
        )
    )
    task.pending_confirmation = None
    transition(task, status="active", actor="customer", reason="confirmation_granted")
    await _save(db, task)
    await _dispatch_due(db, task.task_id, due_at=datetime.now(UTC))
    return task


async def _save(db, task: Task) -> None:
    checkpoint = task.model_dump(mode="json")
    checkpoint["version"] = task.version + 1
    result = await db.execute(
        update(ServiceTask)
        .where(ServiceTask.id == task.task_id, ServiceTask.version == task.version)
        .values(checkpoint=checkpoint, version=task.version + 1)
    )
    if result.rowcount != 1:
        raise TaskConflict("Stale task checkpoint")
    task.version += 1


async def _dispatch_due(db, task_id: str, *, due_at) -> None:
    values: dict = {"due_at": due_at, "lease_token": None, "lease_until": None}
    if due_at is not None:
        values.update({"attempts": 0, "last_error": None})
    await db.execute(
        update(ServiceDispatch).where(ServiceDispatch.task_id == task_id).values(**values)
    )
