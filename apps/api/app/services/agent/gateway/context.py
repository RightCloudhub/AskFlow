"""Execution context supplied by authenticated application code, never by model text."""

from dataclasses import dataclass

from app.services.agent.service.contracts import Scope

ACTOR_AGENT = "agent"
ACTOR_USER = "user"
ACTOR_HUMAN = "human_agent"
ACTOR_SYSTEM = "system"


@dataclass(frozen=True)
class ExecContext:
    scope: Scope
    actor: str = ACTOR_AGENT
    assurance: int = 1
    task_id: str | None = None
    turn_id: str | None = None
    step: str = "step"
    has_confirmation: bool = False
