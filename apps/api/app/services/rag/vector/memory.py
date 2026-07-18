"""In-process cosine vector index (offline-first, no Chroma required)."""

from __future__ import annotations

import math
from typing import Any

from app.services.rag.vector.types import VectorHit, VectorRecord

# Absolute score floor: near-orthogonal offline vectors stay weak for grounding
_MIN_SCORE = 0.0


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na <= 0 or nb <= 0:
        return 0.0
    return float(dot / (na * nb))


class MemoryVectorIndex:
    """Process-local embedding store with absolute cosine scores (not max-norm)."""

    def __init__(self) -> None:
        self._by_id: dict[str, VectorRecord] = {}

    def clear(self) -> None:
        self._by_id.clear()

    def upsert(self, records: list[VectorRecord]) -> int:
        for rec in records:
            self._by_id[rec.id] = rec
        return len(records)

    def delete_by_doc_id(self, doc_id: str) -> int:
        drop = [rid for rid, rec in self._by_id.items() if rec.doc_id == doc_id]
        for rid in drop:
            del self._by_id[rid]
        return len(drop)

    def search(self, query_vec: list[float], top_k: int = 5) -> list[VectorHit]:
        if not query_vec or not self._by_id:
            return []
        scored: list[tuple[float, VectorRecord]] = []
        for rec in self._by_id.values():
            sim = cosine_similarity(query_vec, rec.embedding)
            if sim <= _MIN_SCORE:
                continue
            scored.append((sim, rec))
        scored.sort(key=lambda x: x[0], reverse=True)
        hits: list[VectorHit] = []
        for sim, rec in scored[:top_k]:
            hits.append(
                VectorHit(
                    doc_id=rec.doc_id,
                    source=rec.source,
                    text=rec.text,
                    score=float(sim),
                    meta={**rec.meta, "channel": "vector", "backend": "memory"},
                )
            )
        return hits

    def snapshot_meta(self) -> list[dict[str, Any]]:
        return [
            {"id": r.id, "doc_id": r.doc_id, "source": r.source, **r.meta}
            for r in self._by_id.values()
        ]

    def __len__(self) -> int:
        return len(self._by_id)
