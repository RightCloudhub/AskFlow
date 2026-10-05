"""P1 (M1): intent→goal catalog, direct routes, dedup keys and object lock keys."""

from uuid import NAMESPACE_URL, uuid5

import pytest

from app.models.enums import Intent, Route
from app.services.agent.intake.goals import (
    GOAL_HUMAN_HANDOFF,
    GOAL_ORDER_STATUS,
    GOAL_SPECS,
    GOAL_TICKET_RESOLUTION,
    dedup_key,
    direct_route,
    goal_for_intent,
    object_key_for_task,
)
from app.services.agent.service.contracts import Scope, Task

SCOPE = Scope(organization_id="shop", customer_id="customer")
CONVERSATION = "conv-1"
ORDER_ID = "ORD202401010001"
OTHER_ORDER_ID = "ORD999888777"
EXPECTED_DISTINCT_KEYS = 3

ACTION_INTENTS = {
    Intent.ORDER_QUERY: GOAL_ORDER_STATUS,
    Intent.FAULT_REPORT: GOAL_TICKET_RESOLUTION,
    Intent.COMPLAINT: GOAL_TICKET_RESOLUTION,
    Intent.HANDOFF: GOAL_HUMAN_HANDOFF,
}
DIRECT_INTENTS = {
    Intent.FAQ: Route.RAG,
    Intent.PRODUCT: Route.RAG,
    Intent.OUT_OF_SCOPE: Route.REFUSE,
}


@pytest.mark.parametrize("intent,goal", list(ACTION_INTENTS.items()))
def test_action_intents_map_to_goals(intent, goal):
    assert goal_for_intent(intent) == goal
    assert direct_route(intent) is None


@pytest.mark.parametrize("intent,route", list(DIRECT_INTENTS.items()))
def test_direct_intents_answer_without_task(intent, route):
    assert goal_for_intent(intent) is None
    assert direct_route(intent) == route


def test_goal_catalog_declares_namespace_completion_and_owner():
    for goal, spec in GOAL_SPECS.items():
        assert spec.goal == goal
        assert spec.namespace
        assert spec.completion_condition
        assert spec.owner


def test_order_dedup_key_matches_legacy_task_identity():
    legacy = str(uuid5(NAMESPACE_URL, f"askflow:order:{CONVERSATION}:{ORDER_ID}"))
    key = dedup_key(conversation_id=CONVERSATION, goal=GOAL_ORDER_STATUS, object_key=ORDER_ID)
    assert key == legacy


def test_dedup_key_is_stable_and_scope_sensitive():
    base = dedup_key(conversation_id=CONVERSATION, goal=GOAL_ORDER_STATUS, object_key=ORDER_ID)
    again = dedup_key(conversation_id=CONVERSATION, goal=GOAL_ORDER_STATUS, object_key=ORDER_ID)
    other_object = dedup_key(
        conversation_id=CONVERSATION, goal=GOAL_ORDER_STATUS, object_key=OTHER_ORDER_ID
    )
    other_goal = dedup_key(conversation_id=CONVERSATION, goal=GOAL_TICKET_RESOLUTION)
    assert base == again
    assert len({base, other_object, other_goal}) == EXPECTED_DISTINCT_KEYS


def test_object_key_for_task_uses_goal_namespace():
    order_task = Task(
        scope=SCOPE,
        goal=GOAL_ORDER_STATUS,
        inputs={"order_id": ORDER_ID},
        completion_condition=GOAL_ORDER_STATUS,
        owner="customer_support",
    )
    ticket_task = Task(
        scope=SCOPE,
        goal=GOAL_TICKET_RESOLUTION,
        completion_condition=GOAL_TICKET_RESOLUTION,
        owner="customer_support",
    )
    assert object_key_for_task(order_task) == f"order:{ORDER_ID}"
    assert object_key_for_task(ticket_task) is None
