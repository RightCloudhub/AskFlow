"""Query rewrite: normalize + synonym rules (default); LLM optional (PRD / query-rewrite.md)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from app.core.config import get_settings


@dataclass
class RewriteResult:
    original: str
    rewritten: str
    strategy: str  # none | rule | llm
    expansions: list[str] = field(default_factory=list)
    flags: list[str] = field(default_factory=list)


class QueryRewriter:
    def __init__(self, synonym_path: str | Path | None = None) -> None:
        settings = get_settings()
        path = Path(synonym_path or settings.rewrite_synonym_path)
        if not path.is_absolute():
            here = Path(__file__).resolve()
            candidates = [
                Path.cwd() / path,
                Path.cwd() / "data" / "samples" / "query_synonyms.yaml",
                # rewriter.py → …/AF/apps/api/app/services/rag/query_rewrite
                here.parents[6] / "data" / "samples" / "query_synonyms.yaml",
                here.parents[6] / path,
            ]
            for c in candidates:
                if c.exists():
                    path = c
                    break
        self.groups: list[dict[str, Any]] = []
        if path.exists():
            with path.open(encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            self.groups = list(data.get("groups") or [])

    def rewrite(self, question: str, history: list[dict[str, str]] | None = None) -> RewriteResult:
        _ = history
        original = (question or "").strip()
        normalized = self._normalize(original)
        if not normalized:
            return RewriteResult(original=original, rewritten=original, strategy="none")

        expansions: list[str] = []
        tokens = {normalized}
        for group in self.groups:
            canonical = str(group.get("canonical", ""))
            aliases = [str(a) for a in (group.get("aliases") or [])]
            terms = [canonical, *aliases]
            if any(t and t.lower() in normalized.lower() for t in terms):
                for t in terms:
                    if t and t not in expansions:
                        expansions.append(t)
                        tokens.add(t)

        if expansions:
            # Append expansions without inventing unrelated topics
            rewritten = normalized
            extra = [e for e in expansions if e.lower() not in normalized.lower()]
            if extra:
                rewritten = f"{normalized} {' '.join(extra[:6])}"
            return RewriteResult(
                original=original,
                rewritten=rewritten,
                strategy="rule",
                expansions=expansions,
            )

        return RewriteResult(original=original, rewritten=normalized, strategy="none")

    def _normalize(self, text: str) -> str:
        text = text.strip()
        text = re.sub(r"\s+", " ", text)
        text = re.sub(r"[？?！!。．.]+$", "", text)
        return text
