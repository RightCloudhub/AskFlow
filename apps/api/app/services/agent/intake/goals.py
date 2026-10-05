"""Application-owned goal catalog and stable task/object identities."""

from dataclasses import dataclass
from uuid import NAMESPACE_URL, uuid5

from app.models.enums import Intent, Route
from app.services.agent.service.contracts import Task

GOAL_ORDER_STATUS = "order_status"
GOAL_TICKET_RESOLUTION = "ticket_resolution"
GOAL_HUMAN_HANDOFF = "human_handoff"
GOAL_NOTIFICATION = "notification"
GOAL_REFUND_REQUEST = "refund_request"


@dataclass(frozen=True)
class GoalSpec:
    goal: str
    namespace: str
    completion_condition: str
    owner: str = "customer_support"


GOAL_SPECS = {
    goal: GoalSpec(goal=goal, namespace=namespace, completion_condition=goal)
    for goal, namespace in (
        (GOAL_ORDER_STATUS, "order"),
        (GOAL_TICKET_RESOLUTION, "ticket"),
        (GOAL_HUMAN_HANDOFF, "handoff"),
        (GOAL_NOTIFICATION, "notify"),
        (GOAL_REFUND_REQUEST, "refund"),
    )
}
ACTION_GOALS = {
    Intent.ORDER_QUERY: GOAL_ORDER_STATUS,
    Intent.FAULT_REPORT: GOAL_TICKET_RESOLUTION,
    Intent.COMPLAINT: GOAL_TICKET_RESOLUTION,
    Intent.HANDOFF: GOAL_HUMAN_HANDOFF,
}
DIRECT_ROUTES = {
    Intent.FAQ: Route.RAG,
    Intent.PRODUCT: Route.RAG,
    Intent.OUT_OF_SCOPE: Route.REFUSE,
}


def goal_for_intent(intent: Intent) -> str | None:
    return ACTION_GOALS.get(intent)


def direct_route(intent: Intent) -> Route | None:
    return DIRECT_ROUTES.get(intent)


def dedup_key(*, conversation_id: str, goal: str, object_key: str | None = None) -> str:
    namespace = GOAL_SPECS[goal].namespace
    return str(uuid5(NAMESPACE_URL, f"askflow:{namespace}:{conversation_id}:{object_key or ''}"))


def object_key_for_task(task: Task) -> str | None:
    # All operations on the same order share a lock, including refunds.
    order_id = task.inputs.get("order_id")
    if order_id:
        return f"order:{order_id}"
    return None
