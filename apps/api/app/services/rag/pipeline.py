"""Honest RAG end-to-end (PRD §4.2)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.services.rag.bm25.index import get_default_bm25
from app.services.rag.citations.verify import verify_citations
from app.services.rag.context.assembler import ContextAssembler
from app.services.rag.fusion.rrf import fuse_hits
from app.services.rag.generator.service import CANCELLED_ANSWER, AnswerGenerator
from app.services.rag.grounding.evaluator import GroundingEvaluator
from app.services.rag.query_rewrite.rewriter import QueryRewriter, RewriteResult
from app.services.rag.retrieval_cache import get_retrieval_cache
from app.services.rag.vector.store import VectorStore, ensure_seeded, get_default_vector_store


@dataclass
class RAGResult:
    answer: str
    refused: bool
    refusal_reason: str | None
    confidence: float
    sources: list[dict[str, Any]] = field(default_factory=list)
    rewrite: dict[str, Any] = field(default_factory=dict)
    verification: dict[str, Any] = field(default_factory=dict)
    flags: list[str] = field(default_factory=list)
    context_trace: dict[str, Any] = field(default_factory=dict)


class RAGPipeline:
    def __init__(self, vector: VectorStore | None = None) -> None:
        self.rewriter = QueryRewriter()
        self.vector = vector or get_default_vector_store()
        self.grounding = GroundingEvaluator()
        self.context = ContextAssembler()
        self.generator = AnswerGenerator()

    async def run(
        self,
        question: str,
        *,
        history: list[dict[str, str]] | None = None,
        top_k: int = 5,
        cancel_key: str | None = None,
    ) -> RAGResult:
        history = history or []
        rewrite: RewriteResult = self.rewriter.rewrite(question, history)
        query = rewrite.rewritten

        rewrite_payload = {
            "original": rewrite.original,
            "rewritten": rewrite.rewritten,
            "strategy": rewrite.strategy,
            "expansions": rewrite.expansions,
        }
        cache_flags: list[str] = []
        fused = await self._retrieve_fused(query, top_k=top_k, flags=cache_flags)

        decision = self.grounding.evaluate(fused)
        if not decision.pass_through:
            return RAGResult(
                answer=decision.refusal_message or "",
                refused=True,
                refusal_reason=decision.reason,
                confidence=decision.score,
                sources=decision.sources,
                rewrite=rewrite_payload,
                verification={"result": "skipped", "refusal_reason": decision.reason},
                flags=["refused", f"refusal:{decision.reason}", *cache_flags],
            )

        bundle = self.context.assemble(
            question=question,
            history=history,
            sources=decision.sources,
        )
        answer = await self.generator.generate(
            question=question,
            sources=decision.sources,
            messages=bundle.messages,
            cancel_key=cancel_key,
        )
        verification = verify_citations(answer, decision.sources)
        flags = list(bundle.flags) + cache_flags
        if cancel_key and answer == CANCELLED_ANSWER:
            flags.append("cancelled")
        return RAGResult(
            answer=answer,
            refused=False,
            refusal_reason=None,
            confidence=decision.score,
            sources=decision.sources,
            rewrite=rewrite_payload,
            verification=verification,
            flags=flags,
            context_trace=bundle.trace,
        )

    async def _retrieve_fused(
        self, query: str, *, top_k: int, flags: list[str]
    ) -> list[Any]:
        cache = get_retrieval_cache()
        key = cache.make_key(query, top_k)
        cached = cache.get(key)
        if cached is not None:
            flags.append("retrieval_cache_hit")
            return cached
        await ensure_seeded(self.vector)
        bm25_hits = get_default_bm25().search(query, top_k=top_k)
        vector_hits = await self.vector.search(query, top_k=top_k)
        fused = fuse_hits([bm25_hits, vector_hits], top_k=top_k)
        cache.set(key, fused)
        flags.append("retrieval_cache_miss")
        return fused
