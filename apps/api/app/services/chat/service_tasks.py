"""Create a durable order task in the same transaction as the customer's chat message."""

from datetime import UTC, datetime
from uuid import NAMESPACE_URL, uuid4, uuid5

from sqlalchemy import select

from app.models.service_dispatch import ServiceDispatch
from app.models.service_task import ServiceTask
from app.plugins.runtime import get_app_context
from app.services.agent.harness.policy import Harness
from app.services.agent.identity import customer_scope
from app.services.agent.intent.classifier import IntentClassifier
from app.services.agent.pipeline.context import PipelineResult
from app.services.agent.service.contracts import Task
from app.services.agent.service.inserts import insert_once
from app.services.agent.service.order import ORDER_GOAL
from app.services.agent.service.settings import ServiceSettings
from app.services.agent.slots.state import SlotTracker


async def maybe_create_order_task(db, conversation, *, text: str, history: list,
                                  metadata: dict) -> PipelineResult | None:
    ctx = get_app_context()
    if not ServiceSettings().enabled or ctx is None or not ctx.enabled("agent"):
        return None
    if conversation.status != "active":
        return None
    prep = Harness().prepare(text, history)
    if not prep.allowed:
        return None
    order_id = await _order_request(prep.text, metadata)
    if not order_id:
        return None
    task = await _ensure_task(db, conversation, order_id=order_id)
    run_id = str(uuid4())
    return PipelineResult(
        run_id=run_id, trace_id=run_id, answer=_acknowledgement(task), route="tool",
        intent="order_query", confidence=1.0, flags=["service_task"],
        metadata_patch={"pending_slot": None},
        side_effects={"service_task": {"task_id": task.task_id, "status": task.status}},
    )


async def _order_request(text: str, metadata: dict) -> str | None:
    order_id = SlotTracker().extract_order_id(text)
    intent = await IntentClassifier().classify(text)
    if intent.intent.value in {"handoff", "out_of_scope", "complaint", "fault_report"}:
        return None
    pending = metadata.get("pending_slot")
    pending = pending if isinstance(pending, dict) else {}
    is_order = intent.intent.value == "order_query" or pending.get("intent") == "order_query"
    return order_id if is_order else None


async def _ensure_task(db, conversation, *, order_id: str) -> Task:
    task_id = str(uuid5(NAMESPACE_URL, f"askflow:order:{conversation.id}:{order_id}"))
    task = Task(task_id=task_id, scope=customer_scope(conversation.user_id),
                conversation_id=conversation.id, goal=f"查询订单 {order_id} 的状态",
                inputs={"order_id": order_id}, completion_condition=ORDER_GOAL,
                owner="customer_support")
    await insert_once(db, ServiceTask, key="id", values={
        "id": task_id, "organization_id": task.scope.organization_id,
        "customer_id": task.scope.customer_id, "version": 0,
        "checkpoint": task.model_dump(mode="json"),
    })
    await insert_once(db, ServiceDispatch, key="task_id", values={
        "task_id": task_id, "due_at": datetime.now(UTC), "attempts": 0, "notified_version": -1,
    })
    row = await db.scalar(select(ServiceTask).where(ServiceTask.id == task_id))
    return Task.model_validate(row.checkpoint)


def _acknowledgement(task: Task) -> str:
    if task.status == "resolved":
        return "该查询任务已完成，可在本会话中查看查询结果。"
    if task.status in {"closed_unresolved", "handed_off"}:
        return "该任务已取消或转交人工，可在任务详情中查看处理状态。"
    return f"已记录订单 {task.inputs['order_id']} 的查询任务，将核验归属并查询最新状态，处理进展会显示在本会话中。"
