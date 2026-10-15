"""Shared router support: decision records, canned replies and assurance lookup."""

import time

from app.plugins.runtime import get_app_context
from app.services.agent.assurance import conversation_assurance, user_assurance
from app.services.agent.pipeline.context import PipelineResult
from app.services.agent.router.actions import CONFIRM_WORDS, ROUTE_INTERACTIVE
from app.services.agent.router.decisions import record_decision
from app.services.agent.service.settings import ServiceSettings

MS_PER_SECOND = 1000


class RouterSupport:
    """Mixin: relies on ``self.db``, ``self.harness``, ``self._turn_id``."""

    async def _record(self, conversation, route: str, started, **fields) -> None:
        relation = fields.pop("relation", None)
        await record_decision(
            self.db,
            turn_id=self._turn_id,
            conversation_id=conversation.id,
            route=route,
            active_task_relation=relation,
            latency_ms=int((time.monotonic() - started) * MS_PER_SECOND),
            **fields,
        )

    def _reply(self, answer: str, route: str = ROUTE_INTERACTIVE) -> PipelineResult:
        final = self.harness.finalize(answer)
        return PipelineResult(
            run_id=self._turn_id,
            trace_id=self._turn_id,
            answer=final.text,
            route=route,
            intent=None,
            confidence=1.0,
            flags=list(final.flags),
        )

    def _task_reply(self, answer: str, task, route: str) -> PipelineResult:
        result = self._reply(answer, route=route)
        result.side_effects = {"service_task": {"task_id": task.task_id, "status": task.status}}
        return result

    async def _assurance(self, conversation) -> int:
        base = await user_assurance(self.db, conversation.user_id)
        return conversation_assurance(conversation, base)

    @staticmethod
    def _tasks_enabled() -> bool:
        if not ServiceSettings().enabled:
            return False
        ctx = get_app_context()
        return ctx is None or ctx.enabled("agent")


def is_confirmation(text: str) -> bool:
    lowered = text.strip().lower()
    return any(word in lowered for word in CONFIRM_WORDS)
