"""Create the checkpoint and dispatch within the caller's message transaction."""

from datetime import UTC, datetime

from sqlalchemy import select

from app.models.service_dispatch import ServiceDispatch
from app.models.service_task import ServiceTask
from app.services.agent.identity import customer_scope
from app.services.agent.intake.goals import GOAL_SPECS, dedup_key
from app.services.agent.intake.judge import IntakeDecision
from app.services.agent.service.contracts import Task
from app.services.agent.service.inserts import insert_once
from app.services.agent.service.settings import ServiceSettings


async def open_goal_task(db, conversation, decision: IntakeDecision, *, inputs=None) -> Task | None:
    settings = ServiceSettings()
    if decision.verdict != "goal" or not settings.takes_over(decision.goal):
        return None
    if conversation.status != "active":
        return None
    spec = GOAL_SPECS.get(decision.goal)
    if spec is None:
        return None
    task_id = dedup_key(
        conversation_id=conversation.id, goal=spec.goal, object_key=decision.object_key
    )
    task = Task(
        task_id=task_id,
        scope=customer_scope(conversation.user_id),
        conversation_id=conversation.id,
        goal=spec.goal,
        inputs=inputs or ({"order_id": decision.object_key} if decision.object_key else {}),
        completion_condition=spec.completion_condition,
        owner=spec.owner,
    )
    await insert_once(
        db,
        ServiceTask,
        key="id",
        values={
            "id": task_id,
            "organization_id": task.scope.organization_id,
            "customer_id": task.scope.customer_id,
            "version": 0,
            "checkpoint": task.model_dump(mode="json"),
        },
    )
    await insert_once(
        db,
        ServiceDispatch,
        key="task_id",
        values={
            "task_id": task_id,
            "due_at": datetime.now(UTC),
            "attempts": 0,
            "notified_version": -1,
        },
    )
    row = await db.scalar(select(ServiceTask).where(ServiceTask.id == task_id))
    return Task.model_validate(row.checkpoint)
