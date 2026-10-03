"""Chat adapter for conservative goal intake, preserving the pending-order slot flow."""

from dataclasses import replace
from uuid import uuid4

from app.models.enums import Intent
from app.plugins.runtime import get_app_context
from app.services.agent.harness.policy import Harness
from app.services.agent.intake.goals import (
    GOAL_HUMAN_HANDOFF,
    GOAL_ORDER_STATUS,
    GOAL_TICKET_RESOLUTION,
)
from app.services.agent.intake.judge import judge
from app.services.agent.intake.open_task import open_goal_task
from app.services.agent.intent.classifier import IntentClassifier
from app.services.agent.pipeline.context import PipelineResult
from app.services.agent.pipeline.handlers.ticket import _ticket_title
from app.services.agent.service.settings import ServiceSettings

SUMMARY_MAX_LENGTH = 500
GOAL_ROUTES = {
    GOAL_ORDER_STATUS: "tool",
    GOAL_TICKET_RESOLUTION: "ticket",
    GOAL_HUMAN_HANDOFF: "handoff",
}


async def maybe_create_goal_task(
    db, conversation, *, text: str, history: list, metadata: dict
) -> PipelineResult | None:
    ctx = get_app_context()
    if not ServiceSettings().enabled or ctx is None or not ctx.enabled("agent"):
        return None
    if conversation.status != "active":
        return None
    prep = Harness().prepare(text, history)
    if not prep.allowed:
        return None
    intent = await _classify(prep.text, metadata)
    decision = judge(intent=intent, text=prep.text)
    inputs = _inputs(conversation, decision, text=prep.text, intent=intent.intent.value)
    task = await open_goal_task(db, conversation, decision, inputs=inputs)
    if task is None:
        return None
    run_id = str(uuid4())
    return PipelineResult(
        run_id=run_id,
        trace_id=run_id,
        answer=_acknowledgement(task),
        route=GOAL_ROUTES[decision.goal],
        intent=intent.intent.value,
        confidence=decision.confidence,
        flags=["service_task"],
        metadata_patch={"pending_slot": None},
        side_effects={
            "service_task": {"task_id": task.task_id, "status": task.status},
            "intake": decision.model_dump(),
        },
    )


async def _classify(text: str, metadata: dict):
    intent = await IntentClassifier().classify(text)
    pending = metadata.get("pending_slot")
    if not isinstance(pending, dict) or pending.get("intent") != "order_query":
        return intent
    if intent.intent in {Intent.FAQ, Intent.PRODUCT}:
        return replace(intent, intent=Intent.ORDER_QUERY)
    return intent


def _inputs(conversation, decision, *, text: str, intent: str) -> dict:
    common = {"conversation_id": conversation.id, "user_id": conversation.user_id}
    if decision.goal == GOAL_TICKET_RESOLUTION:
        return {
            **common,
            "title": _ticket_title(intent, text),
            "description": text,
            "ticket_type": intent,
            "priority": "high",
        }
    if decision.goal == GOAL_HUMAN_HANDOFF:
        return {**common, "summary": text[:SUMMARY_MAX_LENGTH], "intent": intent}
    return {}


def _acknowledgement(task) -> str:
    if task.status == "resolved":
        return "该任务已完成，可在本会话中查看处理结果。"
    if task.status in {"closed_unresolved", "handed_off"}:
        return "该任务已取消或转交人工，可在任务详情中查看处理状态。"
    if task.completion_condition == GOAL_ORDER_STATUS:
        return f"已记录订单 {task.inputs['order_id']} 的查询任务，将核验归属并查询最新状态，处理进展会显示在本会话中。"
    return "已记录您的处理请求，处理进展会显示在本会话中。"
