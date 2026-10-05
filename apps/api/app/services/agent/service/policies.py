"""Resolve completion contracts into application-owned agent builders."""

from collections.abc import Callable

from app.services.agent.domains.order import ORDER_GOAL, chat_order_agent
from app.services.agent.domains.support import support_builder
from app.services.agent.intake.goals import GOAL_HUMAN_HANDOFF, GOAL_TICKET_RESOLUTION


class AgentPolicyRegistry:
    def __init__(self):
        self.builders: dict[str, Callable] = {}

    def register(self, goal: str, builder: Callable) -> None:
        if goal in self.builders:
            raise ValueError(f"Duplicate goal: {goal}")
        self.builders[goal] = builder

    def resolve(self, goal: str) -> Callable | None:
        return self.builders.get(goal)


def default_policy_registry() -> AgentPolicyRegistry:
    registry = AgentPolicyRegistry()
    registry.register(ORDER_GOAL, lambda store, task: chat_order_agent(store, task.scope))
    registry.register(GOAL_TICKET_RESOLUTION, support_builder(handoff=False))
    registry.register(GOAL_HUMAN_HANDOFF, support_builder(handoff=True))
    return registry
