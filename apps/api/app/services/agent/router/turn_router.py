"""Priority-ordered turn routing: control → resume → goal match → interactive (arch §4.3)."""

import time

from app.services.agent.harness.policy import Harness
from app.services.agent.router.actions import (
    ROUTE_CLARIFY,
    ROUTE_CONTROL,
    ROUTE_HANDOFF,
    ROUTE_INTERACTIVE,
    ROUTE_REFUSE,
    ROUTE_STEP_UP,
    ROUTE_TASK_CREATE,
    ROUTE_TASK_RESUME,
    RouterAction,
)
from app.services.agent.router.new_intent_flow import NewIntentFlow
from app.services.agent.router.open_task_flow import OpenTaskFlow
from app.services.agent.router.settings import RouterSettings
from app.services.agent.router.support import RouterSupport
from app.services.agent.router.task_ops import open_tasks
from app.services.agent.slots.state import SlotTracker
from app.utils.ids import new_run_id

__all__ = [
    "ROUTE_CLARIFY",
    "ROUTE_CONTROL",
    "ROUTE_HANDOFF",
    "ROUTE_INTERACTIVE",
    "ROUTE_REFUSE",
    "ROUTE_STEP_UP",
    "ROUTE_TASK_CREATE",
    "ROUTE_TASK_RESUME",
    "RouterAction",
    "TurnRouter",
]


class TurnRouter(OpenTaskFlow, NewIntentFlow, RouterSupport):
    def __init__(self, db) -> None:
        self.db = db
        self.settings = RouterSettings()
        self.harness = Harness()
        self.slots = SlotTracker()
        self._turn_id = new_run_id()

    async def route(
        self, *, conversation, text: str, history: list, metadata: dict, turn_id: str | None = None
    ) -> RouterAction:
        started = time.monotonic()
        self._turn_id = turn_id or self._turn_id
        if conversation.status != "active" or not self._tasks_enabled():
            return RouterAction(route=ROUTE_INTERACTIVE)
        prep = self.harness.prepare(text, history)
        if not prep.allowed:
            return RouterAction(route=ROUTE_INTERACTIVE)
        tasks = await open_tasks(self.db, conversation, limit=self.settings.open_task_scan_limit)
        step_up = await self._pending_step_up(
            conversation=conversation, text=prep.text, started=started
        )
        if step_up is not None:
            return step_up
        if tasks:
            action = await self._with_open_tasks(
                conversation=conversation, tasks=tasks, text=prep.text, started=started
            )
            if action is not None:
                return action
        return await self._new_intent(
            conversation=conversation, text=prep.text, metadata=metadata, started=started
        )
