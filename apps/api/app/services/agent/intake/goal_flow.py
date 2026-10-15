"""Shared goal-flow helpers: task inputs, acknowledgements and task-created results."""

from dataclasses import replace

from app.models.enums import Intent
from app.services.agent.intake.goals import (
    GOAL_HUMAN_HANDOFF,
    GOAL_ORDER_STATUS,
    GOAL_TICKET_RESOLUTION,
)
from app.services.agent.intent.classifier import IntentClassifier
from app.services.agent.pipeline.context import PipelineResult
from app.services.agent.pipeline.handlers.ticket import _ticket_title

SUMMARY_MAX_LENGTH = 500
GOAL_ROUTES = {
    GOAL_ORDER_STATUS: "tool",
    GOAL_TICKET_RESOLUTION: "ticket",
    GOAL_HUMAN_HANDOFF: "handoff",
}


async def classify_with_pending_slot(text: str, metadata: dict):
    intent = await IntentClassifier().classify(text)
    pending = metadata.get("pending_slot")
    if not isinstance(pending, dict) or pending.get("intent") != "order_query":
        return intent
    if intent.intent in {Intent.FAQ, Intent.PRODUCT}:
        return replace(intent, intent=Intent.ORDER_QUERY)
    return intent


def goal_inputs(conversation, decision, *, text: str, intent: str) -> dict:
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


def acknowledgement(task) -> str:
    if task.status == "resolved":
        return "该任务已完成，可在本会话中查看处理结果。"
    if task.status in {"closed_unresolved", "handed_off"}:
        return "该任务已取消或转交人工，可在任务详情中查看处理状态。"
    if task.completion_condition == GOAL_ORDER_STATUS:
        return (
            f"已记录订单 {task.inputs['order_id']} 的查询任务，"
            "将核验归属并查询最新状态，处理进展会显示在本会话中。"
        )
    return "已记录您的处理请求，处理进展会显示在本会话中。"


def task_created_result(*, task, decision, intent_result, turn_id: str) -> PipelineResult:
    return PipelineResult(
        run_id=turn_id,
        trace_id=turn_id,
        answer=acknowledgement(task),
        route=GOAL_ROUTES[decision.goal],
        intent=intent_result.intent.value,
        confidence=decision.confidence,
        flags=["service_task"],
        metadata_patch={"pending_slot": None},
        side_effects={
            "service_task": {"task_id": task.task_id, "status": task.status},
            "intake": decision.model_dump(),
        },
    )
