"""Single-message Agent pipeline (PRD §3.2) — table-driven dispatch."""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import Intent, Route
from app.services.agent.cost.ledger import CostLedger
from app.services.agent.harness.policy import Harness
from app.services.agent.intent.classifier import IntentClassifier
from app.services.agent.loop.engine import LoopEngine
from app.services.agent.model_router.router import ModelRouter
from app.services.agent.pipeline.context import PipelineResult, TurnContext
from app.services.agent.pipeline.defaults import resolve_route_handlers
from app.services.agent.pipeline.handlers.clarify import handle_clarify
from app.services.agent.router.decision import RouteResolver
from app.services.agent.slots.state import SlotDecision, SlotTracker
from app.services.rag.pipeline import RAGPipeline
from app.services.tools.registry import registry
from app.utils.ids import new_run_id, new_trace_id

# Re-export for callers/tests
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
        trace_id = new_trace_id()
        ledger = CostLedger(run_id)
        self._seed_cost(ledger)
        flags: list[str] = []

        if conversation_status == "transferred":
            return self._transferred(run_id, trace_id, ledger, flags)

        prep = self.harness.prepare(text, history)
        flags.extend(prep.flags)
        if not prep.allowed:
            return self._blocked(run_id, trace_id, ledger, flags, prep.stop_message or "")

        meta = metadata or {}
        # Tool slot short-circuit only when tools capability is enabled
        if self._tools_enabled():
            slot = self.slots.decide(prep.text, meta)
        else:
            slot = SlotDecision(action="none")
            flags = flags + ["tools_disabled_skip_slot"]

        meta_patch: dict[str, Any] = {}
        if slot.patch:
            meta_patch = self.slots.apply_patch({}, slot.patch)

        if slot.action == "ask":
            return await self._slot_ask(run_id, trace_id, ledger, flags, slot, meta_patch)

        if slot.action == "filled" and slot.order_id:
            return await self._slot_filled(
                run_id, trace_id, ledger, flags, slot.order_id, meta_patch, prep.text
            )

        return await self._classify_and_dispatch(
            run_id, trace_id, ledger, flags, prep.text, prep.history, meta, meta_patch
        )

    def _tools_enabled(self) -> bool:
        """True when tools plugin registered (or no AppContext → full defaults)."""
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
            )

    def _transferred(
        self, run_id: str, trace_id: str, ledger: CostLedger, flags: list[str]
    ) -> PipelineResult:
        return PipelineResult(
            run_id=run_id,
            trace_id=trace_id,
            answer=self.harness.transferred_message(),
            route="noop",
            intent=None,
            confidence=1.0,
            flags=flags + ["transferred_skip_ai"],
            cost=ledger.summary(),
        )

    def _blocked(
        self,
        run_id: str,
        trace_id: str,
        ledger: CostLedger,
        flags: list[str],
        answer: str,
    ) -> PipelineResult:
        return PipelineResult(
            run_id=run_id,
            trace_id=trace_id,
            answer=answer,
            route="blocked",
            intent=None,
            confidence=1.0,
            flags=flags,
            cost=ledger.summary(),
        )

    async def _slot_ask(
        self,
        run_id: str,
        trace_id: str,
        ledger: CostLedger,
        flags: list[str],
        slot: Any,
        meta_patch: dict[str, Any],
    ) -> PipelineResult:
        final = self.harness.finalize(slot.message)
        return PipelineResult(
            run_id=run_id,
            trace_id=trace_id,
            answer=final.text,
            route=Route.TOOL.value,
            intent=Intent.ORDER_QUERY.value,
            confidence=0.9,
            flags=flags + final.flags + ["slot_ask"],
            metadata_patch=meta_patch,
            cost=ledger.summary(),
        )

    async def _slot_filled(
        self,
        run_id: str,
        trace_id: str,
        ledger: CostLedger,
        flags: list[str],
        order_id: str,
        meta_patch: dict[str, Any],
        text: str = "",
    ) -> PipelineResult:
        # Always go through registry — never hard-call handle_tool
        turn = TurnContext(
            run_id=run_id,
            trace_id=trace_id,
            text=text,
            history=[],
            metadata={},
            flags=flags,
            ledger=ledger,
            harness=self.harness,
            slots=self.slots,
            order_id=order_id,
            meta_patch=meta_patch or {"pending_slot": None},
            loop=self.loop,
            rag=self.rag,
        )
        return await self._dispatch(Route.TOOL.value, turn)

    async def _classify_and_dispatch(
        self,
        run_id: str,
        trace_id: str,
        ledger: CostLedger,
        flags: list[str],
        text: str,
        history: list[dict[str, Any]],
        metadata: dict[str, Any],
        meta_patch: dict[str, Any],
    ) -> PipelineResult:
        intent_result = await self.classifier.classify(text, history)
        flags.extend(intent_result.reasons or [])
        resolved = await self.router.resolve(intent_result.intent)
        route_decision = self.harness.choose_route(
            resolved.route,
            confidence=intent_result.confidence,
            needs_clarify=intent_result.needs_clarify,
        )
        flags.extend(route_decision.flags)
        route = route_decision.route

        side_effects: dict[str, Any] = {
            "intent_source": intent_result.source,
            "route_source": resolved.source,
            "policy_version": self.harness.policy_version,
        }

        if route == Route.REFUSE or intent_result.intent == Intent.OUT_OF_SCOPE:
            route_key = Route.REFUSE.value
        else:
            route_key = route.value

        turn = TurnContext(
            run_id=run_id,
            trace_id=trace_id,
            text=text,
            history=history,
            metadata=metadata,
            flags=flags,
            ledger=ledger,
            harness=self.harness,
            slots=self.slots,
            intent_result=intent_result,
            side_effects=side_effects,
            meta_patch=meta_patch,
            loop=self.loop,
            rag=self.rag,
        )
        return await self._dispatch(route_key, turn)

    async def _dispatch(self, route_key: str, turn: TurnContext) -> PipelineResult:
        # Resolve at call-time so profile changes / unit tests without AppContext work
        handler = resolve_route_handlers().get(route_key)
        if handler is None:
            turn.flags = list(turn.flags) + [f"handler_missing:{route_key}"]
            return await handle_clarify(turn)
        return await handler(turn)
