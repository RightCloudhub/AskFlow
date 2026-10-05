"""P1 (M1): intake verdicts — goal / answer / clarify / resume, recorded for audit."""

import pytest

from app.models.enums import Intent
from app.services.agent.intake.judge import judge
from app.services.agent.intent.classifier import IntentResult
from app.services.agent.service.contracts import Scope, Task

SCOPE = Scope(organization_id="shop", customer_id="customer")
CONFIDENCE = 0.7
ORDER_ID = "ORD202401010001"
ORDER_TEXT = f"我的订单号是 {ORDER_ID}"
PLAIN_TEXT = "你们几点上班"

ACTION_INTENTS = [
    (Intent.FAULT_REPORT, "ticket_resolution"),
    (Intent.COMPLAINT, "ticket_resolution"),
    (Intent.HANDOFF, "human_handoff"),
]
DIRECT_INTENTS = [Intent.FAQ, Intent.PRODUCT, Intent.OUT_OF_SCOPE]


def intent_result(intent, *, confidence=CONFIDENCE, needs_clarify=False):
    return IntentResult(
        intent=intent, confidence=confidence, source="rule", needs_clarify=needs_clarify
    )


def waiting_task(goal, *, status="waiting_customer"):
    return Task(
        scope=SCOPE, goal=goal, completion_condition=goal, owner="customer_support", status=status
    )


def test_order_query_with_order_id_becomes_goal():
    decision = judge(intent=intent_result(Intent.ORDER_QUERY), text=ORDER_TEXT)
    assert decision.verdict == "goal"
    assert decision.goal == "order_status"
    assert decision.object_key == ORDER_ID
    assert decision.confidence == CONFIDENCE


def test_order_query_without_order_id_asks_for_clarification():
    decision = judge(intent=intent_result(Intent.ORDER_QUERY), text="帮我查下订单")
    assert decision.verdict == "clarify"
    assert decision.goal is None


@pytest.mark.parametrize("intent,goal", ACTION_INTENTS)
def test_conversation_scoped_intents_open_goals(intent, goal):
    decision = judge(intent=intent_result(intent), text="页面一直报错")
    assert decision.verdict == "goal"
    assert decision.goal == goal
    assert decision.object_key is None


@pytest.mark.parametrize("intent", DIRECT_INTENTS)
def test_direct_intents_are_answered_not_tasked(intent):
    decision = judge(intent=intent_result(intent), text=PLAIN_TEXT)
    assert decision.verdict == "answer"
    assert decision.goal is None


def test_uncertain_classification_prefers_clarification():
    result = intent_result(Intent.ORDER_QUERY, needs_clarify=True)
    decision = judge(intent=result, text=ORDER_TEXT)
    assert decision.verdict == "clarify"


def test_waiting_customer_task_takes_precedence_as_resume():
    open_task = waiting_task("order_status")
    decision = judge(intent=intent_result(Intent.FAQ), text=ORDER_ID, open_task=open_task)
    assert decision.verdict == "resume"
    assert decision.goal == "order_status"
    assert decision.confidence == CONFIDENCE


def test_active_task_does_not_block_new_goal():
    active = waiting_task("order_status", status="active")
    decision = judge(intent=intent_result(Intent.ORDER_QUERY), text=ORDER_TEXT, open_task=active)
    assert decision.verdict == "goal"
