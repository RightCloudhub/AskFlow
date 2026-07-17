"""Query rewrite + Honest RAG grounding (real pipeline path)."""

import pytest

from app.services.rag.bm25.index import BM25Index, combine_relevance, get_default_bm25
from app.services.rag.grounding.evaluator import GroundingEvaluator, REFUSAL_WEAK, REFUSAL_ZERO
from app.services.rag.pipeline import RAGPipeline
from app.services.rag.query_rewrite.rewriter import QueryRewriter


def test_synonym_rewrite_return():
    r = QueryRewriter().rewrite("怎么退换货")
    assert r.strategy in {"rule", "none"}
    if r.strategy == "rule":
        assert "退货" in r.rewritten or any("退" in e for e in r.expansions)


def test_grounding_zero_hit():
    d = GroundingEvaluator().evaluate([])
    assert d.pass_through is False
    assert d.reason == "zero_hit"
    assert d.refusal_message == REFUSAL_ZERO


def test_bm25_does_not_max_normalize_top_to_one():
    """Top hit must not always be ~1.0 just because something matched."""
    # Use default multi-doc seed corpus (tiny 1–2 doc Okapi can collapse IDF to 0)
    idx = get_default_bm25()
    weak = idx.search("今天月球天气如何量子纠缠", top_k=5)
    # Either empty or low absolute score — never forced to 1.0 from max-norm
    if weak:
        assert weak[0].score < 0.35, f"weak query top score inflated: {weak[0].score}"
        assert weak[0].score != pytest.approx(1.0)

    strong = idx.search("退货政策是什么", top_k=5)
    assert strong, "expected hits for FAQ-style query on seed corpus"
    assert strong[0].score >= 0.35
    assert strong[0].score <= 1.0
    # must not be artificially max-normalized to 1.0
    assert strong[0].score < 0.99
    if weak:
        assert strong[0].score > weak[0].score


def test_combine_relevance_requires_coverage():
    # high raw alone with zero coverage stays modest
    assert combine_relevance(10.0, 0.0) < 0.7
    assert combine_relevance(0.1, 0.1) < 0.35


@pytest.mark.asyncio
async def test_rag_faq_hit():
    result = await RAGPipeline().run("退货政策是什么")
    assert result.refused is False, f"unexpected refuse: {result.refusal_reason} conf={result.confidence}"
    assert result.answer
    assert "无法确信" not in result.answer and "无法编造" not in result.answer
    assert len(result.sources) >= 1
    assert result.confidence >= 0.35
    # answer should be grounded in return policy seed, not invented elsewhere
    joined = result.answer + " " + " ".join(s.get("text", "") for s in result.sources)
    assert "退" in joined


@pytest.mark.asyncio
async def test_rag_refuse_unrelated():
    """PRD §12.1 #3: weak/zero evidence → refuse; do not invent from seed docs."""
    question = "今天月球天气如何量子纠缠"
    result = await RAGPipeline().run(question)
    assert result.refused is True, (
        f"expected refusal, got answer={result.answer!r} conf={result.confidence} "
        f"sources={[s.get('source') for s in result.sources]}"
    )
    assert result.refusal_reason in {"weak_evidence", "zero_hit"}
    assert result.answer
    # Must be the fixed refusal template, not extractive synthesis of seed FAQs
    assert result.answer in {REFUSAL_WEAK, REFUSAL_ZERO} or (
        "无法确信" in result.answer or "无法编造" in result.answer
    )
    # Must not invent an answer that presents seed FAQ as if it answers the moon query
    assert "根据知识库资料" not in result.answer
    # confidence for weak path is the weak top score (< threshold) or 0
    assert result.confidence < 0.35 or result.refusal_reason == "zero_hit"


@pytest.mark.asyncio
async def test_seed_index_unrelated_bm25_low():
    hits = get_default_bm25().search("今天月球天气如何量子纠缠", top_k=5)
    if hits:
        assert hits[0].score < 0.35
