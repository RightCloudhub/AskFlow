"""Atomically finish dispatch and append a deduplicated customer-visible chat update."""

from datetime import UTC, datetime
from uuid import NAMESPACE_URL, uuid5

from sqlalchemy import select, update

from app.models.conversation import Conversation, Message
from app.models.service_dispatch import ServiceDispatch
from app.models.service_task import ServiceTask
from app.services.agent.intake.goals import GOAL_ORDER_STATUS, GOAL_TICKET_RESOLUTION
from app.services.agent.service.contracts import Task
from app.services.agent.service.inserts import insert_once


def next_due(task: Task):
    if task.status == "active":
        deadlines = [e.deadline_at for e in task.ledger if e.status == "running" and e.deadline_at]
        return max(deadlines) if deadlines else datetime.now(UTC)
    if task.status == "waiting_external" and (task.wake_condition or "").startswith("retry:"):
        return task.review_at
    return None


async def finish_dispatch(store, claim, task: Task) -> None:
    async with store.sessions.begin() as db:
        changed = await db.execute(
            update(ServiceDispatch)
            .where(
                ServiceDispatch.task_id == claim.task_id,
                ServiceDispatch.lease_token == claim.token,
            )
            .values(
                lease_token=None,
                lease_until=None,
                due_at=next_due(task),
                attempts=0,
                last_error=None,
            )
        )
        if changed.rowcount != 1:
            return
        row = await db.scalar(
            select(ServiceTask).where(ServiceTask.id == task.task_id).with_for_update()
        )
        if row.version != task.version:
            await db.execute(
                update(ServiceDispatch)
                .where(ServiceDispatch.task_id == claim.task_id)
                .values(due_at=datetime.now(UTC))
            )
            return
        job = await db.get(ServiceDispatch, claim.task_id)
        if next_due(task) is None and job.notified_version != task.version:
            await _notify(db, task)
            job.notified_version = task.version


async def _notify(db, task: Task) -> None:
    if task.status in {"closed_unresolved", "handed_off"}:
        return
    conv = await db.scalar(
        select(Conversation)
        .where(
            Conversation.id == task.conversation_id,
            Conversation.user_id == task.scope.customer_id,
            Conversation.status == "active",
        )
        .with_for_update()
    )
    if conv is None:
        return
    content = _result_text(task)
    message_id = str(uuid5(NAMESPACE_URL, f"askflow:task-update:{task.task_id}:{task.version}"))
    await insert_once(
        db,
        Message,
        key="id",
        values={
            "id": message_id,
            "conversation_id": conv.id,
            "role": "assistant",
            "content": content,
            "meta": {
                "service_task": {
                    "task_id": task.task_id,
                    "status": task.status,
                    "version": task.version,
                }
            },
        },
    )


def _result_text(task: Task) -> str:
    if task.status != "resolved":
        return "处理暂未完成，需要支持人员检查；可在任务详情中查看处理状态。"
    if task.completion_condition == GOAL_ORDER_STATUS:
        evidence = task.evidence[-1]
        return f"订单 {evidence.data.get('order_id', '')} 查询完成，状态：{evidence.data.get('status', '')}。"
    if task.completion_condition == GOAL_TICKET_RESOLUTION:
        return "工单已登记，您可在「我的工单」中查看进度。"
    return "您的请求已处理完成，可在任务详情中查看处理状态。"
