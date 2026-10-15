"""Priority 1-3: control intents, confirmations and continuations for open tasks (arch §9.4)."""

from app.services.agent.gateway.confirmation import validate_confirmation_for_hash
from app.services.agent.router.actions import (
    CANCEL_ACK,
    CANCEL_BLOCKED_ACK,
    CONFIRM_ACK,
    CONFIRM_EXPIRED,
    CONFIRM_QUESTION,
    RELATED_ACK,
    REMINDER,
    RESUME_ACK,
    ROUTE_CONTROL,
    ROUTE_HANDOFF,
    ROUTE_INTERACTIVE,
    ROUTE_TASK_RESUME,
    RouterAction,
)
from app.services.agent.router.control_intent import (
    CONTROL_CANCEL,
    CONTROL_HUMAN,
    detect_control,
)
from app.services.agent.router.support import is_confirmation
from app.services.agent.router.task_ops import (
    CONTROLLABLE_STATUSES,
    cancel_open_task,
    grant_confirmation,
    resume_task,
)


class OpenTaskFlow:
    """Mixin: relies on ``self.db``, ``self.slots`` and RouterSupport helpers."""

    async def _with_open_tasks(self, *, conversation, tasks: list, text: str, started):
        control = detect_control(text)
        if control == CONTROL_HUMAN:
            await self._record(conversation, ROUTE_HANDOFF, started, method="rule", relation="control")
            return RouterAction(route=ROUTE_HANDOFF, relation="control")
        if control == CONTROL_CANCEL and self._cancel_targets(text, tasks):
            return await self._cancel(conversation=conversation, tasks=tasks, started=started)
        newest = tasks[0]
        if newest.status == "waiting_customer" and newest.pending_confirmation is not None:
            return await self._confirmation_reply(
                conversation=conversation, task=newest, text=text, started=started
            )
        if newest.status == "waiting_customer":
            return await self._resume(conversation=conversation, task=newest, started=started)
        extracted = self.slots.extract_order_id(text)
        if extracted and any(t.inputs.get("order_id") == extracted for t in tasks):
            await self._record(
                conversation, ROUTE_TASK_RESUME, started,
                goal_key=newest.goal, method="rule", relation="modification",
            )
            return RouterAction(
                route=ROUTE_TASK_RESUME,
                handled=self._task_reply(RELATED_ACK, newest, ROUTE_TASK_RESUME),
                relation="modification",
            )
        await self._record(conversation, ROUTE_INTERACTIVE, started, method="rule", relation="unrelated")
        return RouterAction(
            route=ROUTE_INTERACTIVE,
            reminder=REMINDER.format(goal=newest.goal),
            relation="unrelated",
        )

    def _cancel_targets(self, text: str, tasks: list) -> bool:
        extracted = self.slots.extract_order_id(text)
        if extracted is None:
            return True
        return any(t.inputs.get("order_id") == extracted for t in tasks)

    async def _cancel(self, *, conversation, tasks: list, started) -> RouterAction:
        target = next((t for t in tasks if t.status in CONTROLLABLE_STATUSES), None)
        if target is None:
            await self._record(conversation, ROUTE_CONTROL, started, method="rule", relation="control")
            return RouterAction(route=ROUTE_CONTROL, handled=self._reply(CANCEL_BLOCKED_ACK))
        await cancel_open_task(self.db, target)
        await self._record(
            conversation, ROUTE_CONTROL, started,
            goal_key=target.goal, method="rule", relation="control",
        )
        return RouterAction(
            route=ROUTE_CONTROL, handled=self._task_reply(CANCEL_ACK, target, ROUTE_CONTROL)
        )

    async def _confirmation_reply(self, *, conversation, task, text: str, started) -> RouterAction:
        pending = task.pending_confirmation
        if not is_confirmation(text):
            return await self._answer_relation(
                conversation=conversation, task=task, started=started, answer=CONFIRM_QUESTION
            )
        valid = await validate_confirmation_for_hash(
            self.db,
            pending.token,
            scope_id=task.task_id,
            step=pending.step,
            expected_args_hash=pending.args_hash,
        )
        if not valid:
            return await self._answer_relation(
                conversation=conversation, task=task, started=started, answer=CONFIRM_EXPIRED
            )
        await grant_confirmation(self.db, task)
        return await self._answer_relation(
            conversation=conversation, task=task, started=started, answer=CONFIRM_ACK
        )

    async def _answer_relation(self, *, conversation, task, started, answer: str) -> RouterAction:
        await self._record(
            conversation, ROUTE_TASK_RESUME, started,
            goal_key=task.goal, method="rule", relation="answer",
        )
        return RouterAction(
            route=ROUTE_TASK_RESUME,
            handled=self._task_reply(answer, task, ROUTE_TASK_RESUME),
            relation="answer",
        )

    async def _resume(self, *, conversation, task, started) -> RouterAction:
        await resume_task(self.db, task)
        return await self._answer_relation(
            conversation=conversation, task=task, started=started, answer=RESUME_ACK
        )
