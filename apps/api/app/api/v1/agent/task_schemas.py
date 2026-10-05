"""Public task projections exclude internal evidence, arguments and operational logs."""

from uuid import UUID

from pydantic import AwareDatetime, Field

from app.services.agent.service.contracts import Record, Task, TaskStatus
from app.services.agent.service.control import unsettled

MAX_CANCELLATION_REASON = 500


class TaskSummary(Record):
    task_id: str
    goal: str
    status: TaskStatus
    version: int
    review_at: AwareDatetime | None
    has_unsettled_operations: bool


class TaskPage(Record):
    items: list[TaskSummary]
    next_cursor: str | None


class CancelRequest(Record):
    expected_version: int = Field(ge=0, strict=True)
    reason: str = Field(min_length=1, max_length=MAX_CANCELLATION_REASON)


class AcceptRequest(Record):
    expected_version: int = Field(ge=0, strict=True)
    handoff_id: UUID


def summarize(task: Task) -> TaskSummary:
    return TaskSummary(
        task_id=task.task_id,
        goal=task.goal,
        status=task.status,
        version=task.version,
        review_at=task.review_at,
        has_unsettled_operations=unsettled(task),
    )
