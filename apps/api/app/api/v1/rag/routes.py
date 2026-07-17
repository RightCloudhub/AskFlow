"""Synchronous RAG query endpoint (PRD §7.1)."""

from __future__ import annotations

from fastapi import APIRouter

from app.core.deps import CurrentUser
from app.middleware.metrics import RAG_REFUSAL, REWRITE_TOTAL
from app.schemas.agent import RAGQueryRequest, RAGQueryResponse, RAGSource
from app.services.rag.pipeline import RAGPipeline

router = APIRouter()


@router.post("/query", response_model=RAGQueryResponse)
async def rag_query(payload: RAGQueryRequest, user: CurrentUser) -> RAGQueryResponse:
    _ = user
    result = await RAGPipeline().run(payload.question, top_k=payload.top_k)
    strategy = result.rewrite.get("strategy", "none")
    REWRITE_TOTAL.labels(strategy=strategy, status="ok").inc()
    if result.refused and result.refusal_reason:
        RAG_REFUSAL.labels(reason=result.refusal_reason).inc()
    return RAGQueryResponse(
        answer=result.answer,
        refused=result.refused,
        refusal_reason=result.refusal_reason,
        confidence=result.confidence,
        sources=[RAGSource(**s) for s in result.sources],
        rewrite=result.rewrite,
        verification=result.verification,
    )
