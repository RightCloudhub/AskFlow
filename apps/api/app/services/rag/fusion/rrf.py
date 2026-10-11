"""Multi-channel fusion (PRD §4.2).

Ranks by Reciprocal Rank Fusion but **preserves absolute channel scores** for
grounding. Never max-normalizes the result set so top hit is always 1.0.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

RRF_K = 60
DEFAULT_TOP_K = 5


@dataclass
class FusedHit:
    doc_id: str
    source: str
    text: str
    score: float
    meta: dict[str, Any]


def _hit_key(hit: Any) -> tuple[str, str]:
    """A chunk is identified by its document and its full text (D-07: no prefix truncation)."""
    return hit.doc_id, hit.text


def _keep_best(fused: dict[tuple[str, str], FusedHit], key: tuple[str, str], hit: Any) -> None:
    """Grounding sees each chunk's best absolute score across channels."""
    current = fused.get(key)
    if current is None:
        fused[key] = FusedHit(hit.doc_id, hit.source, hit.text, hit.score, dict(hit.meta))
    elif hit.score > current.score:
        current.score = hit.score


def fuse_hits(
    channels: list[list[Any]],
    *,
    k: int = RRF_K,
    top_k: int = DEFAULT_TOP_K,
) -> list[FusedHit]:
    rrf: dict[tuple[str, str], float] = {}
    fused: dict[tuple[str, str], FusedHit] = {}
    for channel in channels:
        for rank, hit in enumerate(channel):
            key = _hit_key(hit)
            rrf[key] = rrf.get(key, 0.0) + 1.0 / (k + rank + 1)
            _keep_best(fused, key, hit)
    positive = [key for key in rrf if fused[key].score > 0]
    if not positive:
        return []
    selected = sorted(positive, key=rrf.__getitem__, reverse=True)[:top_k]
    strongest = max(positive, key=lambda key: fused[key].score)
    # D-19: the best absolute grounding hit always survives the RRF cut
    if strongest not in selected:
        selected[-1] = strongest
    result = [fused[key] for key in selected]
    result.sort(key=lambda h: h.score, reverse=True)
    return result
