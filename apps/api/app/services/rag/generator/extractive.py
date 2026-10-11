"""Offline extractive answer: the sentences that best answer the question, with citations.

Used when no LLM is configured (or the LLM call fails). Earlier versions pasted every
grounded chunk verbatim, so a question about refunds also printed the loyalty-points policy.
Now each source is split into sentences (markdown headings dropped), scored by query
coverage, and only the best few overlapping sentences are kept, in source order, tagged ``[n]``.
"""

from __future__ import annotations

import re
from typing import Any

from app.services.rag.bm25.index import query_coverage

MAX_SENTENCES = 3
SENTENCE_SPLIT = re.compile(r"(?<=[。！？!?；;])|\n+")
HEADING = re.compile(r"^\s*#+\s*")
INTRO = "根据知识库资料："
OUTRO = "如需进一步说明，请继续提问。"


def _sentences(source: dict[str, Any]) -> list[tuple[str, int]]:
    index = int(source.get("index", 1))
    parts = SENTENCE_SPLIT.split(str(source.get("text", "")))
    return [(p.strip(), index) for p in parts if p.strip() and not HEADING.match(p)]


def extractive_answer(question: str, sources: list[dict[str, Any]]) -> str:
    candidates = [pair for src in sources for pair in _sentences(src)]
    scored = [(query_coverage(question, text), pos) for pos, (text, _) in enumerate(candidates)]
    # Highest coverage first; on ties the earlier (better-ranked) source wins
    ranked = sorted((p for p in scored if p[0] > 0), key=lambda p: (-p[0], p[1]))
    chosen = sorted(pos for _, pos in ranked[:MAX_SENTENCES])
    if not chosen:
        # Grounding passed but no sentence overlaps lexically: answer from the top source.
        chosen = [pos for pos, (_, idx) in enumerate(candidates) if idx == candidates[0][1]]
    lines = [f"- {candidates[pos][0]} [{candidates[pos][1]}]" for pos in chosen]
    return "\n".join([INTRO, "", *lines, "", OUTRO])
