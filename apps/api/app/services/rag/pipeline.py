"""Honest RAG end-to-end (PRD §4.2)."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from app.core.config import Settings, get_settings
from app.services.rag.bm25.index import get_default_bm25
from app.services.rag.citations.verify import verify_citations
from app.services.rag.context.assembler import ContextAssembler
from app.services.rag.fusion.rrf import fuse_hits
from app.services.rag.generator.service import CANCELLED_ANSWER, AnswerGenerator
from app.services.rag.generator.token_sink import emit_sources
from app.services.rag.grounding.evaluator import GroundingEvaluator
from app.services.rag.query_rewrite.rewriter import QueryRewriter, RewriteResult
from app.services.rag.rerank import apply_rerank
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
    def __init__(self, vector: VectorStore | None = None, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
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
        memory_block: str | None = None,
        filters: dict | None = None,
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
        fused = await self._retrieve_fused(query, top_k=top_k, flags=cache_flags, filters=filters)
        fused = apply_rerank(
            fused, query, enabled=self.settings.rerank_enabled, top_n=self.settings.rerank_top_n
        )

        decision = self.grounding.evaluate(fused)
        if not decision.pass_through:
            return _refusal_result(decision, rewrite_payload, cache_flags)
        return await self._answer(
            question,
            history=history,
            sources=decision.sources,
            confidence=decision.score,
            rewrite_payload=rewrite_payload,
            cache_flags=cache_flags,
            cancel_key=cancel_key,
            memory_block=memory_block,
        )

    async def _answer(
        self,
        question: str,
        *,
        history: list,
        sources: list,
        confidence: float,
        rewrite_payload: dict,
        cache_flags: list[str],
        cancel_key: str | None,
        memory_block: str | None,
    ) -> RAGResult:
        await emit_sources(sources)
        bundle = self.context.assemble(
            question=question,
            history=history,
            sources=sources,
            memory_block=memory_block,
        )
        answer = await self.generator.generate(
            question=question, sources=sources, messages=bundle.messages, cancel_key=cancel_key
        )
        verification = verify_citations(answer, sources)
        flags = list(bundle.flags) + cache_flags
        if cancel_key and answer == CANCELLED_ANSWER:
            flags.append("cancelled")
        return RAGResult(
            answer=answer,
            refused=False,
            refusal_reason=None,
            confidence=confidence,
            sources=sources,
            rewrite=rewrite_payload,
            verification=verification,
            flags=flags,
            context_trace=bundle.trace,
        )

    async def _retrieve_fused(
        self, query: str, *, top_k: int, flags: list[str], filters: dict | None = None
    ) -> list[Any]:
        cache = get_retrieval_cache()
        key = cache.make_key(query, top_k, filters)
        cached = cache.get(key)
        if cached is not None:
            flags.append("retrieval_cache_hit")
            return cached
        await ensure_seeded(self.vector)
        # Local BM25 (CPU) and vector search (often a network hop) run concurrently
        bm25_hits, vector_hits = await asyncio.gather(
            asyncio.to_thread(get_default_bm25().search, query, top_k),
            self.vector.search(query, top_k=top_k),
        )
        bm25_hits = _filter_hits(bm25_hits, filters)
        vector_hits = _filter_hits(vector_hits, filters)
        fused = fuse_hits([bm25_hits, vector_hits], top_k=top_k)
        cache.set(key, fused)
        flags.append("retrieval_cache_miss")
        return fused


def _refusal_result(decision, rewrite_payload: dict, cache_flags: list[str]) -> RAGResult:
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


def _filter_hits(hits: list, filters: dict | None) -> list:
    """Pre-ranking metadata filters: language, product, ACL groups, validity window (arch §4.7)."""
    if not filters:
        return hits
    return [hit for hit in hits if _allowed(getattr(hit, "meta", {}) or {}, filters)]


def _allowed(meta: dict, filters: dict) -> bool:
    if not _field_matches(meta, filters, "language"):
        return False
    if not _field_matches(meta, filters, "product"):
        return False
    if not _acl_allowed(meta, filters):
        return False
    return _within_validity(meta, filters)


def _field_matches(meta: dict, filters: dict, key: str) -> bool:
    wanted = filters.get(key)
    return not wanted or not meta.get(key) or meta[key] == wanted


def _acl_allowed(meta: dict, filters: dict) -> bool:
    required = filters.get("acl_groups")
    if not required:
        return True
    doc_groups = set(meta.get("acl_groups") or [])
    return not doc_groups or bool(doc_groups.intersection(required))


def _within_validity(meta: dict, filters: dict) -> bool:
    valid_at = _parse_time(filters.get("valid_at")) or datetime.now(UTC)
    valid_from = _parse_time(meta.get("valid_from"))
    if valid_from and valid_at < valid_from:
        return False
    valid_to = _parse_time(meta.get("valid_to"))
    return not (valid_to and valid_at >= valid_to)


def _parse_time(value):
    if value is None or isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value))
    except ValueError:
        return None
