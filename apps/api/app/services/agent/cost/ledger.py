"""Best-effort cost ledger (PRD §4.17) — failures never block main path."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class CostEntry:
    purpose: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    estimated_usd: float = 0.0
    cache_hit: bool = False
    meta: dict[str, Any] = field(default_factory=dict)


# Rough default price table USD / 1M tokens (prompt, completion)
DEFAULT_PRICES: dict[str, tuple[float, float]] = {
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4o": (2.50, 10.0),
    "text-embedding-3-small": (0.02, 0.0),
}


class CostLedger:
    def __init__(self, run_id: str) -> None:
        self.run_id = run_id
        self.entries: list[CostEntry] = []

    def record(
        self,
        *,
        purpose: str,
        model: str,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        cache_hit: bool = False,
        meta: dict[str, Any] | None = None,
    ) -> None:
        try:
            prices = DEFAULT_PRICES.get(model, (1.0, 3.0))
            usd = (prompt_tokens * prices[0] + completion_tokens * prices[1]) / 1_000_000
            self.entries.append(
                CostEntry(
                    purpose=purpose,
                    model=model,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    estimated_usd=usd,
                    cache_hit=cache_hit,
                    meta=meta or {},
                )
            )
        except Exception:
            # never raise
            return

    def summary(self) -> dict[str, Any]:
        usage = [e for e in self.entries if e.meta.get("phase") != "budget"]
        billed = usage if usage else self.entries
        return {
            "run_id": self.run_id,
            "total_prompt_tokens": sum(e.prompt_tokens for e in billed),
            "total_completion_tokens": sum(e.completion_tokens for e in billed),
            "estimated_usd": round(sum(e.estimated_usd for e in billed), 6),
            "calls": len(self.entries),
            "entries": [
                {
                    "purpose": e.purpose,
                    "model": e.model,
                    "prompt_tokens": e.prompt_tokens,
                    "completion_tokens": e.completion_tokens,
                    "estimated_usd": e.estimated_usd,
                    "cache_hit": e.cache_hit,
                    "phase": e.meta.get("phase", "usage"),
                }
                for e in self.entries
            ],
        }
