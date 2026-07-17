"""Multi-channel fusion (PRD §4.2).

Ranks by Reciprocal Rank Fusion but **preserves absolute channel scores** for
grounding. Never max-normalizes the result set so top hit is always 1.0.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class FusedHit:
    doc_id: str
    source: str
    text: str
    score: float
    meta: dict[str, Any]


def fuse_hits(
    channels: list[list[Any]],
    *,
    k: int = 60,
    top_k: int = 5,
) -> list[FusedHit]:
    rrf: dict[str, float] = {}
    best_score: dict[str, float] = {}
    payload: dict[str, FusedHit] = {}

    for channel in channels:
        for rank, hit in enumerate(channel):
            key = f"{hit.doc_id}:{hit.text[:64]}"
            rrf[key] = rrf.get(key, 0.0) + 1.0 / (k + rank + 1)
            ch_score = float(getattr(hit, "score", 0.0))
            if key not in best_score or ch_score > best_score[key]:
                best_score[key] = ch_score
            if key not in payload:
                payload[key] = FusedHit(
                    doc_id=hit.doc_id,
                    source=hit.source,
                    text=hit.text,
                    score=0.0,
                    meta=dict(getattr(hit, "meta", {}) or {}),
                )

    if not rrf:
        return []

    # Rank by RRF agreement; expose grounding score as best absolute channel score
    ordered = sorted(rrf.items(), key=lambda x: x[1], reverse=True)[:top_k]
    result: list[FusedHit] = []
    for key, _rrf_s in ordered:
        hit = payload[key]
        hit.score = float(best_score.get(key, 0.0))
        if hit.score <= 0:
            continue
        result.append(hit)
    # Re-sort by absolute score for grounding top-1
    result.sort(key=lambda h: h.score, reverse=True)
    return result
