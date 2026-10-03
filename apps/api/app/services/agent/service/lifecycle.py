"""Application-only wakeup boundary; event authentication belongs to the caller."""

from datetime import UTC, datetime

from app.services.agent.service.contracts import Record, Scope
from app.services.agent.service.store import TaskStore


class VerifiedWakeup(Record):
    """Construct only after verifying event origin and mapping it to an owned task."""

    task_id: str
    scope: Scope
    condition: str


async def wake_task(store: TaskStore, event: VerifiedWakeup) -> bool:
    task = await store.load(event.task_id, event.scope)
    if task.status not in {"waiting_external", "waiting_customer"}:
        return False
    if task.wake_condition != event.condition:
        return False
    if event.condition.startswith("retry:") and task.review_at:
        if datetime.now(UTC) < task.review_at:
            return False
    task.status, task.wake_condition, task.review_at = "active", None, None
    await store.save(task)
    return True
