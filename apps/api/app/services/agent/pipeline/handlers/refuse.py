"""Refuse / out-of-scope route handler."""

from __future__ import annotations

from app.middleware.metrics import OUT_OF_SCOPE_TOTAL
from app.models.enums import Intent, Route
from app.services.agent.pipeline.context import PipelineResult, TurnContext


async def handle_refuse(ctx: TurnContext) -> PipelineResult:
    OUT_OF_SCOPE_TOTAL.inc()
    final = ctx.harness.finalize(ctx.harness.out_of_scope_message())
    confidence = ctx.intent_result.confidence if ctx.intent_result else 1.0
    return PipelineResult(
        run_id=ctx.run_id,
        trace_id=ctx.trace_id,
        answer=final.text,
        route=Route.REFUSE.value,
        intent=Intent.OUT_OF_SCOPE.value,
        confidence=confidence,
        flags=list(ctx.flags) + final.flags + ["out_of_scope"],
        refused=True,
        side_effects=dict(ctx.side_effects),
        cost=ctx.ledger.summary(),
    )
