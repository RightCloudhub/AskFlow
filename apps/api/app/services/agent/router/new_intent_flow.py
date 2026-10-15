"""Priorities 4-8: goal match, confidence bands, step-up and task creation (arch §4.3)."""

from app.models.enums import Intent
from app.services.agent.assurance import LEVEL_AUTHENTICATED, elevation_patch
from app.services.agent.gateway.settings import GatewaySettings
from app.services.agent.intake.goal_flow import (
    classify_with_pending_slot,
    goal_inputs,
    task_created_result,
)
from app.services.agent.intake.goals import GOAL_SPECS, goal_for_intent
from app.services.agent.intake.judge import judge
from app.services.agent.intake.open_task import open_goal_task
from app.services.agent.otp import issue_otp, otp_active, verify_otp
from app.services.agent.router.actions import (
    CLARIFY_GOAL,
    PENDING_STEP_UP_KEY,
    PENDING_TEXT_MAX,
    ROUTE_CLARIFY,
    ROUTE_HANDOFF,
    ROUTE_INTERACTIVE,
    ROUTE_REFUSE,
    ROUTE_STEP_UP,
    ROUTE_TASK_CREATE,
    STEP_UP_BAD_CODE,
    STEP_UP_CODE_HINT,
    STEP_UP_EXPIRED,
    STEP_UP_REPLY,
    RouterAction,
)
from app.services.agent.service.settings import ServiceSettings


class NewIntentFlow:
    """Mixin: relies on ``self.db``, ``self.settings`` and RouterSupport helpers."""

    async def _pending_step_up(self, *, conversation, text: str, started):
        pending = (conversation.metadata_json or {}).get(PENDING_STEP_UP_KEY)
        if not isinstance(pending, dict):
            return None
        if await verify_otp(self.db, conversation_id=conversation.id, code=text.strip()):
            return await self._finish_step_up(
                conversation=conversation, pending=pending, started=started
            )
        await self._record(conversation, ROUTE_STEP_UP, started, method="rule")
        if await otp_active(self.db, conversation_id=conversation.id):
            return RouterAction(route=ROUTE_STEP_UP, handled=self._reply(STEP_UP_BAD_CODE))
        reply = self._reply(STEP_UP_EXPIRED)
        reply.metadata_patch = {PENDING_STEP_UP_KEY: None}
        return RouterAction(route=ROUTE_STEP_UP, handled=reply)

    async def _finish_step_up(self, *, conversation, pending: dict, started) -> RouterAction:
        patch = {
            PENDING_STEP_UP_KEY: None,
            **elevation_patch(LEVEL_AUTHENTICATED, GatewaySettings().assurance_ttl_seconds),
        }
        goal = pending.get("goal")
        spec = GOAL_SPECS.get(goal)
        stored_text = str(pending.get("text") or "")
        if spec is None:
            return self._patched_reply(STEP_UP_EXPIRED, ROUTE_STEP_UP, patch)
        intent_result = await classify_with_pending_slot(stored_text, {})
        decision = judge(intent=intent_result, text=stored_text)
        if decision.verdict != "goal" or decision.goal != goal:
            await self._record(conversation, ROUTE_CLARIFY, started, goal_key=goal, method="step_up")
            return self._patched_reply(CLARIFY_GOAL.format(goal=goal), ROUTE_CLARIFY, patch)
        inputs = goal_inputs(
            conversation, decision, text=stored_text, intent=intent_result.intent.value
        )
        task = await open_goal_task(
            self.db, conversation, decision, inputs=inputs, assurance=LEVEL_AUTHENTICATED
        )
        if task is None:
            return self._patched_reply(STEP_UP_EXPIRED, ROUTE_STEP_UP, patch)
        await self._record(
            conversation, ROUTE_TASK_CREATE, started,
            goal_key=goal, goal_version=spec.version,
            confidence=decision.confidence, method="step_up", slots=dict(task.inputs),
        )
        result = task_created_result(
            task=task, decision=decision, intent_result=intent_result, turn_id=self._turn_id
        )
        result.metadata_patch = {**result.metadata_patch, **patch}
        return RouterAction(route=ROUTE_TASK_CREATE, handled=result)

    def _patched_reply(self, answer: str, route: str, patch: dict) -> RouterAction:
        reply = self._reply(answer, route=route)
        reply.metadata_patch = patch
        return RouterAction(route=route, handled=reply)

    async def _new_intent(self, *, conversation, text: str, metadata: dict, started) -> RouterAction:
        intent = await classify_with_pending_slot(text, metadata)
        method = intent.source or "classifier"
        if intent.needs_clarify:
            await self._record(
                conversation, ROUTE_CLARIFY, started, confidence=intent.confidence, method=method
            )
            return RouterAction(route=ROUTE_CLARIFY)
        goal = goal_for_intent(intent.intent)
        if goal is None:
            route = self._direct_route(intent.intent)
            await self._record(
                conversation, route, started, confidence=intent.confidence, method=method
            )
            return RouterAction(route=route)
        if not ServiceSettings().takes_over(goal):
            await self._record(
                conversation, ROUTE_INTERACTIVE, started,
                goal_key=goal, confidence=intent.confidence, method=method,
            )
            return RouterAction(route=ROUTE_INTERACTIVE)
        spec = GOAL_SPECS[goal]
        assurance = await self._assurance(conversation)
        if assurance < spec.required_assurance:
            return await self._start_step_up(
                conversation=conversation, text=text, intent=intent,
                spec=spec, started=started, assurance=assurance,
            )
        if intent.confidence < self.settings.high_confidence:
            await self._record(
                conversation, ROUTE_CLARIFY, started,
                goal_key=goal, goal_version=spec.version,
                confidence=intent.confidence, method=method,
            )
            # Medium band: the pipeline clarifies or starts the slot flow (arch §4.3 priority 5).
            return RouterAction(route=ROUTE_CLARIFY)
        return await self._create_task(
            conversation=conversation, text=text, intent=intent,
            goal=goal, assurance=assurance, started=started,
        )

    @staticmethod
    def _direct_route(intent: Intent) -> str:
        if intent == Intent.OUT_OF_SCOPE:
            return ROUTE_REFUSE
        if intent == Intent.HANDOFF:
            return ROUTE_HANDOFF
        return ROUTE_INTERACTIVE

    async def _start_step_up(
        self, *, conversation, text: str, intent, spec, started, assurance: int
    ) -> RouterAction:
        issue = await issue_otp(
            self.db,
            user_id=conversation.user_id,
            conversation_id=conversation.id,
            channel="chat",
        )
        pending = {
            "goal": spec.goal,
            "text": text[:PENDING_TEXT_MAX],
            "challenge_id": issue.challenge_id,
            "expires_at": issue.expires_at.isoformat(),
        }
        answer = STEP_UP_REPLY
        if issue.code:
            answer = f"{STEP_UP_REPLY}{STEP_UP_CODE_HINT.format(code=issue.code)}"
        reply = self._reply(answer, route=ROUTE_STEP_UP)
        reply.metadata_patch = {PENDING_STEP_UP_KEY: pending}
        await self._record(
            conversation, ROUTE_STEP_UP, started,
            goal_key=spec.goal, goal_version=spec.version,
            confidence=intent.confidence, method="rule",
            identity_requirement={
                "required": spec.required_assurance,
                "current": assurance,
                "action": "STEP_UP",
            },
        )
        return RouterAction(route=ROUTE_STEP_UP, handled=reply)

    async def _create_task(
        self, *, conversation, text: str, intent, goal: str, assurance: int, started
    ) -> RouterAction:
        decision = judge(intent=intent, text=text)
        if decision.verdict != "goal":
            await self._record(
                conversation, ROUTE_CLARIFY, started,
                goal_key=goal, confidence=intent.confidence,
            )
            return RouterAction(route=ROUTE_CLARIFY)
        inputs = goal_inputs(conversation, decision, text=text, intent=intent.intent.value)
        task = await open_goal_task(
            self.db, conversation, decision, inputs=inputs, assurance=assurance
        )
        if task is None:
            await self._record(
                conversation, ROUTE_INTERACTIVE, started,
                goal_key=goal, confidence=intent.confidence,
            )
            return RouterAction(route=ROUTE_INTERACTIVE)
        spec = GOAL_SPECS[goal]
        await self._record(
            conversation, ROUTE_TASK_CREATE, started,
            goal_key=goal, goal_version=spec.version,
            confidence=intent.confidence, method=intent.source or "classifier",
            slots=dict(task.inputs),
        )
        result = task_created_result(
            task=task, decision=decision, intent_result=intent, turn_id=self._turn_id
        )
        return RouterAction(route=ROUTE_TASK_CREATE, handled=result)
