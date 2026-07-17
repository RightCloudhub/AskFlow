"""Lightweight lexical fallback vector store for MVP (Chroma swap-in later)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.services.rag.bm25.index import get_default_bm25


@dataclass
class VectorHit:
    doc_id: str
    source: str
    text: str
    score: float
    meta: dict[str, Any]


class VectorStore:
    """MVP: reuses BM25 as semantic stand-in until embeddings/Chroma are wired.

    Does not re-inflate scores — passes through absolute BM25 relevance.
    """

    async def search(self, query: str, top_k: int = 5) -> list[VectorHit]:
        hits = get_default_bm25().search(query, top_k=top_k)
        return [
            VectorHit(
                doc_id=h.doc_id,
                source=h.source,
                text=h.text,
                score=h.score,
                meta=h.meta,
            )
            for h in hits
        ]
