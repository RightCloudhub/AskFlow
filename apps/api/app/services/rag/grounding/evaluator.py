"""Evidence grounding / refusal (PRD §4.2.2) — never invent when weak."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.core.config import Settings, get_settings

REFUSAL_WEAK = (
    "根据现有知识库，我无法确信地回答该问题。"
    "以下是相关度较低的参考片段，建议换种说法提问，或转人工处理。"
)
REFUSAL_ZERO = (
    "知识库中没有找到与该问题相关的资料，我无法编造答案。"
    "您可以换个关键词试试，或申请转人工。"
)


@dataclass
class GroundingDecision:
    pass_through: bool
    score: float
    reason: str | None = None
    refusal_message: str | None = None
    sources: list[dict[str, Any]] = field(default_factory=list)


class GroundingEvaluator:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def evaluate(self, hits: list[Any]) -> GroundingDecision:
        if not hits:
            return GroundingDecision(
                pass_through=False,
                score=0.0,
                reason="zero_hit",
                refusal_message=REFUSAL_ZERO,
                sources=[],
            )

        # Drop near-zero noise before thresholding
        usable = [h for h in hits if float(getattr(h, "score", 0.0)) > 0]
        if not usable:
            return GroundingDecision(
                pass_through=False,
                score=0.0,
                reason="zero_hit",
                refusal_message=REFUSAL_ZERO,
                sources=[],
            )

        top_score = float(getattr(usable[0], "score", 0.0))
        sources = [
            {
                "index": i + 1,
                "doc_id": getattr(h, "doc_id", None),
                "source": getattr(h, "source", "unknown"),
                "text": getattr(h, "text", ""),
                "score": float(getattr(h, "score", 0.0)),
            }
            for i, h in enumerate(usable)
        ]

        # Absolute threshold — scores must NOT be max-normalized per query
        if (
            len(usable) < self.settings.grounding_min_hits
            or top_score < self.settings.grounding_threshold
        ):
            weak_n = self.settings.grounding_weak_sources
            return GroundingDecision(
                pass_through=False,
                score=top_score,
                reason="weak_evidence",
                refusal_message=REFUSAL_WEAK,
                sources=sources[:weak_n],
            )

        return GroundingDecision(pass_through=True, score=top_score, sources=sources)
