"""HANDOFF route — emit enqueue side-effect only."""

from __future__ import annotations

from app.models.enums import Route
from app.services.agent.pipeline.context import PipelineResult, TurnContext

SUMMARY_MAX = 500


async def handle_handoff(ctx: TurnContext) -> PipelineResult:
    intent = ctx.intent_result.intent.value if ctx.intent_result else "handoff"
    confidence = ctx.intent_result.confidence if ctx.intent_result else 0.9
    se = {
        **ctx.side_effects,
        "handoff": {
            "action": "enqueue",
            "summary": ctx.text[:SUMMARY_MAX],
            "intent": intent,
        },
    }
    final = ctx.harness.finalize(
        "正在为您转接人工客服，请稍候。排队中您仍可补充信息。"
    )
    return PipelineResult(
        run_id=ctx.run_id,
        trace_id=ctx.trace_id,
        answer=final.text,
        route=Route.HANDOFF.value,
        intent=intent,
        confidence=confidence,
        flags=list(ctx.flags) + final.flags,
        side_effects=se,
        cost=ctx.ledger.summary(),
    )
