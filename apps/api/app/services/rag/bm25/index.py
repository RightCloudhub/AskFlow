"""In-process BM25 keyword retrieval (PRD §4.2).

Scores are absolute-ish in [0, 1] (soft BM25 + query coverage), NOT max-normalized
within the current result set — otherwise the top hit is always ~1.0 and grounding
never sees weak evidence (PRD §12.1 #3).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from rank_bm25 import BM25Okapi

# Soft ceiling for raw Okapi BM25 → (0, 1): score = raw / (raw + K)
_BM25_SOFT_K = 3.0
# Weight of lexical coverage vs soft BM25 in final hit score
_COVERAGE_WEIGHT = 0.45


def _tokenize(text: str) -> list[str]:
    """CJK unigrams + bigrams + latin words. Bigrams make weak char hits less dominant."""
    lower = (text or "").lower()
    chars = re.findall(r"[\u4e00-\u9fff]", lower)
    words = re.findall(r"[A-Za-z0-9_]+", lower)
    tokens: list[str] = list(words)
    tokens.extend(chars)
    for i in range(len(chars) - 1):
        tokens.append(chars[i] + chars[i + 1])
    return tokens or ([lower] if lower else [])


def _soft_bm25(raw: float) -> float:
    if raw <= 0:
        return 0.0
    return float(raw / (raw + _BM25_SOFT_K))


def _significant_tokens(tokens: list[str]) -> set[str]:
    """Prefer multi-char / latin tokens for coverage; fall back to all tokens."""
    sig = {t for t in tokens if len(t) >= 2}
    return sig if sig else set(tokens)


def query_coverage(query: str, doc_text: str) -> float:
    q = _significant_tokens(_tokenize(query))
    if not q:
        return 0.0
    d = set(_tokenize(doc_text))
    return len(q & d) / len(q)


def combine_relevance(raw_bm25: float, coverage: float) -> float:
    soft = _soft_bm25(raw_bm25)
    cov = max(0.0, min(1.0, coverage))
    # Both signals required: weak char matches cannot alone push past threshold
    return float((1.0 - _COVERAGE_WEIGHT) * soft + _COVERAGE_WEIGHT * cov)


@dataclass
class SearchHit:
    doc_id: str
    source: str
    text: str
    score: float
    meta: dict[str, Any]


class BM25Index:
    def __init__(self) -> None:
        self._docs: list[dict[str, Any]] = []
        self._corpus_tokens: list[list[str]] = []
        self._bm25: BM25Okapi | None = None

    def clear(self) -> None:
        self._docs.clear()
        self._corpus_tokens.clear()
        self._bm25 = None

    def add_documents(self, docs: list[dict[str, Any]]) -> None:
        for d in docs:
            text = str(d.get("text", ""))
            self._docs.append(d)
            self._corpus_tokens.append(_tokenize(text))
        if self._corpus_tokens:
            self._bm25 = BM25Okapi(self._corpus_tokens)

    def search(self, query: str, top_k: int = 5) -> list[SearchHit]:
        if not self._bm25 or not self._docs:
            return []
        raw_scores = self._bm25.get_scores(_tokenize(query))
        ranked = sorted(enumerate(raw_scores), key=lambda x: x[1], reverse=True)[: max(top_k * 3, top_k)]
        hits: list[SearchHit] = []
        for idx, raw in ranked:
            if raw <= 0:
                continue
            d = self._docs[idx]
            text = str(d.get("text", ""))
            cov = query_coverage(query, text)
            score = combine_relevance(float(raw), cov)
            if score <= 0:
                continue
            hits.append(
                SearchHit(
                    doc_id=str(d.get("doc_id", "")),
                    source=str(d.get("source", "unknown")),
                    text=text,
                    score=score,
                    meta={
                        **{k: v for k, v in d.items() if k not in {"text"}},
                        "raw_bm25": float(raw),
                        "coverage": cov,
                    },
                )
            )
        hits.sort(key=lambda h: h.score, reverse=True)
        return hits[:top_k]


# Process-global default index (seeded with sample FAQ for MVP bootstrap)
_default_index: BM25Index | None = None


def get_default_bm25() -> BM25Index:
    global _default_index
    if _default_index is None:
        _default_index = BM25Index()
        _default_index.add_documents(seed_documents())
    return _default_index


def reset_default_bm25() -> None:
    """Test helper: rebuild seeded index after mutations."""
    global _default_index
    _default_index = None
    try:
        from app.services.rag.vector.store import reset_default_vector_store

        reset_default_vector_store()
    except Exception:
        pass


def seed_documents() -> list[dict[str, Any]]:
    """Shared FAQ seed payloads for BM25 + vector bootstrap."""
    return [
        {
            "doc_id": "seed-return",
            "source": "退货政策.md",
            "text": "退货政策：自签收之日起7天内可申请退货，商品需保持未使用、包装完整。退款将在审核通过后3-5个工作日原路返回。",
            "generation": 1,
            "chunk_index": 0,
        },
        {
            "doc_id": "seed-shipping",
            "source": "物流说明.md",
            "text": "物流与配送：默认使用顺丰/京东物流，下单后48小时内发货。会员包邮门槛为实付满99元。可在订单详情查看运单号与物流状态。",
            "generation": 1,
            "chunk_index": 0,
        },
        {
            "doc_id": "seed-login",
            "source": "账号帮助.md",
            "text": "登录问题：若无法登录，请确认邮箱或手机号是否正确，并尝试重置密码。连续失败5次将临时锁定15分钟。",
            "generation": 1,
            "chunk_index": 0,
        },
        {
            "doc_id": "seed-invoice",
            "source": "发票须知.md",
            "text": "发票：支持电子普通发票与增值税专用发票。订单完成后可在「我的订单-申请开票」提交抬头与税号。",
            "generation": 1,
            "chunk_index": 0,
        },
    ]
