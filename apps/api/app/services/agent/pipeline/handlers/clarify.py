"""Clarify route handler."""

from __future__ import annotations

from app.models.enums import Route
from app.services.agent.pipeline.context import PipelineResult, TurnContext


async def handle_clarify(ctx: TurnContext) -> PipelineResult:
    final = ctx.harness.finalize(ctx.harness.clarify_message())
    intent = ctx.intent_result.intent.value if ctx.intent_result else None
    confidence = ctx.intent_result.confidence if ctx.intent_result else 0.0
    return PipelineResult(
        run_id=ctx.run_id,
        trace_id=ctx.trace_id,
        answer=final.text,
        route=Route.CLARIFY.value,
        intent=intent,
        confidence=confidence,
        flags=list(ctx.flags) + final.flags,
        side_effects=dict(ctx.side_effects),
        cost=ctx.ledger.summary(),
    )
