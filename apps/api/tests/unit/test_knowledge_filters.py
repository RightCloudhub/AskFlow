"""Pre-ranking metadata filters, reranker and cache-key isolation (arch §4.7)."""

from dataclasses import dataclass, field

from app.services.rag.pipeline import _filter_hits
from app.services.rag.rerank import apply_rerank
from app.services.rag.retrieval_cache import RetrievalCache


@dataclass
class Hit:
    doc_id: str
    source: str
    text: str
    score: float
    meta: dict = field(default_factory=dict)


def hit(meta: dict, text: str = "chunk") -> Hit:
    return Hit(doc_id="d1", source="s", text=text, score=0.5, meta=meta)


def test_language_filter():
    hits = [hit({"language": "en"}), hit({"language": "zh"}), hit({})]
    kept = _filter_hits(hits, {"language": "en"})
    assert len(kept) == 2  # unlabeled docs stay visible


def test_product_filter():
    hits = [hit({"product": "jacket"}), hit({"product": "boots"})]
    kept = _filter_hits(hits, {"product": "jacket"})
    assert [h.meta["product"] for h in kept] == ["jacket"]


def test_acl_groups_filter():
    hits = [hit({"acl_groups": ["hr"]}), hit({"acl_groups": ["sales"]}), hit({"acl_groups": []})]
    kept = _filter_hits(hits, {"acl_groups": ["sales"]})
    assert [h.meta["acl_groups"] for h in kept] == [["sales"], []]


def test_validity_window_filter():
    hits = [
        hit({"valid_from": "2999-01-01T00:00:00+00:00"}),
        hit({"valid_to": "2000-01-01T00:00:00+00:00"}),
        hit({"valid_from": "2000-01-01T00:00:00+00:00", "valid_to": "2999-01-01T00:00:00+00:00"}),
    ]
    kept = _filter_hits(hits, {"valid_at": "2026-10-15T00:00:00+00:00"})
    assert kept == [hits[2]]


def test_no_filters_returns_all():
    hits = [hit({"language": "en"}), hit({"language": "zh"})]
    assert _filter_hits(hits, None) == hits


def test_rerank_reorders_by_coverage_and_is_optional():
    hits = [
        hit({}, text="unrelated words"),
        hit({}, text="return policy for jackets"),
    ]
    reranked = apply_rerank(hits, "return policy jackets", enabled=True, top_n=2)
    assert reranked[0].text == "return policy for jackets"
    assert apply_rerank(hits, "return policy jackets", enabled=False, top_n=2) == hits


def test_cache_key_includes_filters():
    cache = RetrievalCache(ttl_seconds=60, max_entries=10)
    base = cache.make_key("q", 5)
    assert base != cache.make_key("q", 5, {"language": "en"})
    assert cache.make_key("q", 5, {"language": "en"}) != cache.make_key("q", 5, {"language": "zh"})
