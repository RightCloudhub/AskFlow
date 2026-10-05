"""Customer task visibility/cancellation and authenticated staff takeover."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.v1.agent.task_schemas import (
    AcceptRequest,
    CancelRequest,
    TaskPage,
    TaskSummary,
    summarize,
)
from app.core import database
from app.core.deps import CurrentUser, require_agent_or_admin
from app.models.user import User
from app.services.agent.identity import customer_scope
from app.services.agent.service.control import (
    HandoffAcceptance,
    InvalidTransition,
    accept_handoff,
    cancel_task,
)
from app.services.agent.service.store import (
    DEFAULT_TASK_PAGE_SIZE,
    MAX_TASK_PAGE_SIZE,
    TaskConflict,
    TaskStore,
)

router = APIRouter()
staff_router = APIRouter()


def task_error(exc: Exception) -> HTTPException:
    if isinstance(exc, LookupError):
        return HTTPException(status.HTTP_404_NOT_FOUND, "task_not_found")
    return HTTPException(status.HTTP_409_CONFLICT, "task_state_conflict")


@router.get("", response_model=TaskPage)
async def list_tasks(
    user: CurrentUser,
    *,
    after: UUID | None = None,
    limit: int = Query(DEFAULT_TASK_PAGE_SIZE, ge=1, le=MAX_TASK_PAGE_SIZE),
):
    rows = await TaskStore(database.SessionLocal).list(
        customer_scope(user.id),
        limit=limit,
        after=str(after) if after else None,
    )
    cursor = rows[-1].task_id if len(rows) == limit else None
    return TaskPage(items=[summarize(row) for row in rows], next_cursor=cursor)


@router.get("/{task_id}", response_model=TaskSummary)
async def get_task(task_id: UUID, user: CurrentUser):
    try:
        return summarize(
            await TaskStore(database.SessionLocal).load(str(task_id), customer_scope(user.id))
        )
    except LookupError as exc:
        raise task_error(exc) from exc


@router.post("/{task_id}/cancel", response_model=TaskSummary)
async def cancel(task_id: UUID, payload: CancelRequest, user: CurrentUser):
    try:
        result = await cancel_task(
            TaskStore(database.SessionLocal),
            str(task_id),
            scope=customer_scope(user.id),
            expected_version=payload.expected_version,
            reason=payload.reason,
        )
        return summarize(result)
    except (LookupError, TaskConflict, InvalidTransition) as exc:
        raise task_error(exc) from exc


@staff_router.post("/{task_id}/accept-handoff", response_model=TaskSummary)
async def accept(
    task_id: UUID, payload: AcceptRequest, user: User = Depends(require_agent_or_admin)
):
    try:
        result = await accept_handoff(
            TaskStore(database.SessionLocal),
            HandoffAcceptance(
                task_id=str(task_id),
                handoff_id=str(payload.handoff_id),
                actor_id=user.id,
                expected_version=payload.expected_version,
            ),
        )
        return summarize(result)
    except (LookupError, TaskConflict, InvalidTransition) as exc:
        raise task_error(exc) from exc
