"""Honest RAG end-to-end (PRD §4.2)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.services.rag.bm25.index import get_default_bm25
from app.services.rag.citations.verify import verify_citations
from app.services.rag.context.assembler import ContextAssembler
from app.services.rag.fusion.rrf import fuse_hits
from app.services.rag.generator.service import AnswerGenerator
from app.services.rag.grounding.evaluator import GroundingEvaluator
from app.services.rag.query_rewrite.rewriter import QueryRewriter, RewriteResult
from app.services.rag.vector.store import VectorStore


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
    def __init__(self) -> None:
        self.rewriter = QueryRewriter()
        self.vector = VectorStore()
        self.grounding = GroundingEvaluator()
        self.context = ContextAssembler()
        self.generator = AnswerGenerator()

    async def run(
        self,
        question: str,
        *,
        history: list[dict[str, str]] | None = None,
        top_k: int = 5,
    ) -> RAGResult:
        history = history or []
        rewrite: RewriteResult = self.rewriter.rewrite(question, history)
        query = rewrite.rewritten

        bm25_hits = get_default_bm25().search(query, top_k=top_k)
        vector_hits = await self.vector.search(query, top_k=top_k)
        fused = fuse_hits([bm25_hits, vector_hits], top_k=top_k)

        decision = self.grounding.evaluate(fused)
        rewrite_payload = {
            "original": rewrite.original,
            "rewritten": rewrite.rewritten,
            "strategy": rewrite.strategy,
            "expansions": rewrite.expansions,
        }

        if not decision.pass_through:
            return RAGResult(
                answer=decision.refusal_message or "",
                refused=True,
                refusal_reason=decision.reason,
                confidence=decision.score,
                sources=decision.sources,
                rewrite=rewrite_payload,
                verification={"result": "skipped", "refusal_reason": decision.reason},
                flags=["refused", f"refusal:{decision.reason}"],
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
        )
        verification = verify_citations(answer, decision.sources)
        return RAGResult(
            answer=answer,
            refused=False,
            refusal_reason=None,
            confidence=decision.score,
            sources=decision.sources,
            rewrite=rewrite_payload,
            verification=verification,
            flags=bundle.flags,
            context_trace=bundle.trace,
        )
