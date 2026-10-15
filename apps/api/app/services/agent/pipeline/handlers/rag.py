"""RAG route handler."""

from __future__ import annotations

from app.models.enums import Route
from app.services.agent.pipeline.context import PipelineResult, TurnContext


async def handle_rag(ctx: TurnContext) -> PipelineResult:
    from app.services.rag.pipeline import RAGPipeline

    rag = ctx.rag if ctx.rag is not None else RAGPipeline()
    kwargs: dict = {"history": ctx.history, "cancel_key": ctx.cancel_key}
    memory_block = await _memory_block(ctx)
    if memory_block is not None and isinstance(rag, RAGPipeline):
        kwargs["memory_block"] = memory_block
    result = await rag.run(ctx.text, **kwargs)
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


async def _memory_block(ctx: TurnContext) -> str | None:
    """Top-k relevant customer facts injected as a short known-about-user block (arch §4.8)."""
    if ctx.db is None or not ctx.user_id:
        return None
    from sqlalchemy import select

    from app.models.agent_memory import AgentMemory
    from app.services.agent.identity import customer_scope
    from app.services.agent.memory.facts import fact_view
    from app.services.agent.memory.records import memory_scope
    from app.services.agent.memory.settings import MemorySettings

    settings = MemorySettings()
    scope = customer_scope(ctx.user_id)
    rows = await ctx.db.scalars(
        select(AgentMemory).where(*memory_scope(scope, kind="fact"))
    )
    active = [
        view
        for view in (fact_view(row) for row in rows)
        if view.status == "active" and view.value
    ][: settings.top_k]
    if not active:
        return None
    block = "；".join(f"{view.key}={view.value}" for view in active)
    return block[: settings.prompt_max_chars]
