"""RAG route handler."""

from __future__ import annotations

from app.models.enums import Route
from app.services.agent.pipeline.context import PipelineResult, TurnContext


async def handle_rag(ctx: TurnContext) -> PipelineResult:
    rag = ctx.rag
    if rag is None:
        from app.services.rag.pipeline import RAGPipeline

        rag = RAGPipeline()
    result = await rag.run(ctx.text, history=ctx.history, cancel_key=ctx.cancel_key)
    final = ctx.harness.finalize(result.answer)
    flags = list(ctx.flags) + list(result.flags) + list(final.flags)
    intent = ctx.intent_result.intent.value if ctx.intent_result else None
    confidence = ctx.intent_result.confidence if ctx.intent_result else 0.0
    return PipelineResult(
        run_id=ctx.run_id,
        trace_id=ctx.trace_id,
        answer=final.text,
        route=Route.RAG.value,
        intent=intent,
        confidence=confidence,
        flags=flags,
        sources=result.sources,
        rewrite=result.rewrite,
        verification=result.verification,
        answer_confidence=result.confidence,
        refused=result.refused,
        side_effects=dict(ctx.side_effects),
        cost=ctx.ledger.summary(),
    )
