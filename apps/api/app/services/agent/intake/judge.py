"""Classify intake without granting execution permissions."""

from typing import Literal

from app.services.agent.intake.goals import GOAL_ORDER_STATUS, direct_route, goal_for_intent
from app.services.agent.intent.classifier import IntentResult
from app.services.agent.service.contracts import Record, Task
from app.services.agent.slots.state import SlotTracker


class IntakeDecision(Record):
    verdict: Literal["goal", "answer", "clarify", "resume"]
    goal: str | None = None
    object_key: str | None = None
    confidence: float
    reason: str


def judge(*, intent: IntentResult, text: str, open_task: Task | None = None) -> IntakeDecision:
    base = {"confidence": intent.confidence}
    if open_task is not None and open_task.status == "waiting_customer":
        return IntakeDecision(
            **base,
            verdict="resume",
            goal=open_task.completion_condition,
            reason="Answer to the waiting task",
        )
    if intent.needs_clarify:
        return IntakeDecision(**base, verdict="clarify", reason="Uncertain intent")
    goal = goal_for_intent(intent.intent)
    if goal is None:
        verdict = "answer" if direct_route(intent.intent) else "clarify"
        return IntakeDecision(**base, verdict=verdict, reason="No business action identified")
    object_key = SlotTracker().extract_order_id(text) if goal == GOAL_ORDER_STATUS else None
    if goal == GOAL_ORDER_STATUS and object_key is None:
        return IntakeDecision(**base, verdict="clarify", reason="Order identifier required")
    return IntakeDecision(
        **base,
        verdict="goal",
        goal=goal,
        object_key=object_key,
        reason="Business action identified",
    )
