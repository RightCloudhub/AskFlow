"""Single-message Agent pipeline (PRD §3.2) — table-driven dispatch."""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import Intent, Route
from app.services.agent.cost.ledger import CostLedger
from app.services.agent.harness.policy import Harness
from app.services.agent.intent.classifier import IntentClassifier, IntentResult
from app.services.agent.loop.engine import LoopEngine
from app.services.agent.model_router.router import ModelRouter
from app.services.agent.pipeline.context import (
    PipelineResult,
    TurnContext,
    TurnIds,
    TurnPayload,
)
from app.services.agent.pipeline.defaults import resolve_route_handlers
from app.services.agent.pipeline.handlers.clarify import handle_clarify
from app.services.agent.pipeline.slot_gate import (
    SlotGateOutcome,
    attach_meta_patch,
    evaluate_slot_gate,
)
from app.services.agent.pipeline.turn_results import (
    blocked_result,
    slot_abandon_result,
    slot_ask_result,
    transferred_result,
)
from app.services.agent.router.decision import RouteResolver
from app.services.agent.slots.state import SlotTracker
from app.services.rag.pipeline import RAGPipeline
from app.services.tools.registry import registry
from app.utils.ids import new_run_id, new_trace_id

__all__ = ["MessagePipeline", "PipelineResult"]

COST_PURPOSES = (
    "intent_classify",
    "query_rewrite",
    "rag_generate",
    "handoff_summary",
)


class MessagePipeline:
    def __init__(self, db: AsyncSession | None = None) -> None:
        self.db = db
        self.harness = Harness()
        self.classifier = IntentClassifier()
        self.router = RouteResolver(db)
        self.slots = SlotTracker()
        self.rag = RAGPipeline()
        self.model_router = ModelRouter()
        self.loop = LoopEngine(registry.as_loop_map())

    async def handle(
        self,
        text: str,
        *,
        history: list[dict[str, Any]] | None = None,
        metadata: dict[str, Any] | None = None,
        conversation_status: str = "active",
    ) -> PipelineResult:
        run_id = new_run_id()
        ledger = CostLedger(run_id)
        self._seed_cost(ledger)
        ids = TurnIds(
            run_id=run_id,
            trace_id=new_trace_id(),
            ledger=ledger,
            flags=[],
        )

        if conversation_status == "transferred":
            return transferred_result(ids, self.harness)

        prep = self.harness.prepare(text, history)
        ids.flags.extend(prep.flags)
        if not prep.allowed:
            return blocked_result(ids, prep.stop_message or "")

        payload = TurnPayload(
            text=prep.text,
            history=prep.history,
            metadata=metadata or {},
        )
        if not self._tools_enabled():
            ids.flags.append("tools_disabled_skip_slot")
            return await self._classify_and_dispatch(ids, payload)

        gate = await evaluate_slot_gate(
            self.slots,
            payload.text,
            payload.metadata,
            history=payload.history,
            classify=self.classifier.classify,
        )
        return await self._apply_slot_gate(ids, payload, gate)

    async def _apply_slot_gate(
        self,
        ids: TurnIds,
        payload: TurnPayload,
        gate: SlotGateOutcome,
    ) -> PipelineResult:
        if gate.kind == "ask" and gate.decision is not None:
            return slot_ask_result(
                ids, self.harness, gate.decision.message, gate.meta_patch
            )
        if gate.kind == "filled" and gate.decision and gate.decision.order_id:
            payload.meta_patch = gate.meta_patch
            return await self._slot_filled(ids, payload, gate.decision.order_id)
        if gate.kind == "abandon" and gate.decision is not None:
            return slot_abandon_result(
                ids, self.harness, gate.decision.message, gate.meta_patch
            )
        payload.meta_patch = gate.meta_patch
        if gate.kind == "continue" and gate.intent_result is not None:
            return await self._dispatch_known_intent(ids, payload, gate.intent_result)
        return await self._classify_and_dispatch(ids, payload)

    def _tools_enabled(self) -> bool:
        from app.plugins.runtime import get_app_context

        ctx = get_app_context()
        if ctx is None:
            return True
        if "tool" in ctx.route_handlers:
            return True
        return "tools" in ctx.features

    def _seed_cost(self, ledger: CostLedger) -> None:
        for purpose in COST_PURPOSES:
            sel = self.model_router.pick(purpose)
            ledger.record(
                purpose=sel.purpose,
                model=sel.model,
                prompt_tokens=0,
                completion_tokens=0,
                meta={"phase": "budget"},
            )

    async def _slot_filled(
        self,
        ids: TurnIds,
        payload: TurnPayload,
        order_id: str,
    ) -> PipelineResult:
        turn = TurnContext(
            run_id=ids.run_id,
            trace_id=ids.trace_id,
            text=payload.text,
            history=[],
            metadata={},
            flags=ids.flags,
            ledger=ids.ledger,
            harness=self.harness,
            slots=self.slots,
            order_id=order_id,
            meta_patch=payload.meta_patch or {"pending_slot": None},
            loop=self.loop,
            rag=self.rag,
        )
        return await self._dispatch(Route.TOOL.value, turn)

    async def _classify_and_dispatch(
        self,
        ids: TurnIds,
        payload: TurnPayload,
    ) -> PipelineResult:
        intent_result = await self.classifier.classify(payload.text, payload.history)
        return await self._dispatch_known_intent(ids, payload, intent_result)

    async def _dispatch_known_intent(
        self,
        ids: TurnIds,
        payload: TurnPayload,
        intent_result: IntentResult,
    ) -> PipelineResult:
        flags = list(ids.flags) + list(intent_result.reasons or [])
        resolved = await self.router.resolve(intent_result.intent)
        route_decision = self.harness.choose_route(
            resolved.route,
            confidence=intent_result.confidence,
            needs_clarify=intent_result.needs_clarify,
        )
        flags.extend(route_decision.flags)
        route = route_decision.route
        if route == Route.REFUSE or intent_result.intent == Intent.OUT_OF_SCOPE:
            route_key = Route.REFUSE.value
        else:
            route_key = route.value
        turn = TurnContext(
            run_id=ids.run_id,
            trace_id=ids.trace_id,
            text=payload.text,
            history=payload.history,
            metadata=payload.metadata,
            flags=flags,
            ledger=ids.ledger,
            harness=self.harness,
            slots=self.slots,
            intent_result=intent_result,
            side_effects={
                "intent_source": intent_result.source,
                "route_source": resolved.source,
                "policy_version": self.harness.policy_version,
            },
            meta_patch=payload.meta_patch,
            loop=self.loop,
            rag=self.rag,
        )
        return await self._dispatch(route_key, turn)

    async def _dispatch(self, route_key: str, turn: TurnContext) -> PipelineResult:
        handler = resolve_route_handlers().get(route_key)
        if handler is None:
            turn.flags = list(turn.flags) + [f"handler_missing:{route_key}"]
            result = await handle_clarify(turn)
        else:
            result = await handler(turn)
        return attach_meta_patch(result, turn.meta_patch)
