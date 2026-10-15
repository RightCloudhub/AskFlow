"""Deterministic offline reranker; a cross-encoder service can replace it later (arch §4.7)."""

import re

TOKEN_PATTERN = re.compile(r"[a-z0-9]+|[一-鿿]")


class LexicalReranker:
    """Query-token coverage with an RRF-order tiebreak; never invents scores."""

    def rerank(self, query: str, hits: list, *, top_n: int) -> list:
        query_tokens = set(TOKEN_PATTERN.findall(query.lower()))
        if not query_tokens:
            return hits[:top_n]
        scored = []
        for index, hit in enumerate(hits):
            tokens = set(TOKEN_PATTERN.findall(str(getattr(hit, "text", "")).lower()))
            coverage = len(query_tokens & tokens) / len(query_tokens)
            scored.append((coverage, -index, hit))
        scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
        return [hit for _, _, hit in scored[:top_n]]


def apply_rerank(hits: list, query: str, *, enabled: bool, top_n: int) -> list:
    if not enabled or not hits:
        return hits
    return LexicalReranker().rerank(query, hits, top_n=top_n)
