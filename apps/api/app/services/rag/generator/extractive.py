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
DUPLICATE_OVERLAP = 0.7
SENTENCE_SPLIT = re.compile(r"(?<=[。！？!?；;])|\n+")
HEADING = re.compile(r"^\s*#+\s*")
INTRO = "根据知识库资料："
OUTRO = "如需进一步说明，请继续提问。"


def _sentences(source: dict[str, Any]) -> list[tuple[str, int]]:
    index = int(source.get("index", 1))
    parts = SENTENCE_SPLIT.split(str(source.get("text", "")))
    return [(p.strip(), index) for p in parts if p.strip() and not HEADING.match(p)]


def _bigrams(text: str) -> set[str]:
    chars = re.sub(r"[\s\W_]+", "", text)
    return {chars[i : i + 2] for i in range(len(chars) - 1)} or {chars}


def is_near_duplicate(a: str, b: str) -> bool:
    """Same fact phrased twice across documents.

    Overlap coefficient on character bigrams (shared / smaller set): rewordings such as
    "仓库验收通过后 3-5 个工作日原路返回" vs "审核通过后3-5个工作日原路返回" score ~0.72,
    unrelated policy sentences stay below 0.1.
    """
    x, y = _bigrams(a), _bigrams(b)
    return len(x & y) / min(len(x), len(y)) >= DUPLICATE_OVERLAP


def _pick(candidates: list[tuple[str, int]], ranked: list[tuple[float, int]]) -> list[int]:
    picked: list[int] = []
    for _, pos in ranked:
        text = candidates[pos][0]
        if any(is_near_duplicate(text, candidates[p][0]) for p in picked):
            continue
        picked.append(pos)
        if len(picked) == MAX_SENTENCES:
            break
    return sorted(picked)


def extractive_answer(question: str, sources: list[dict[str, Any]]) -> str:
    candidates = [pair for src in sources for pair in _sentences(src)]
    scored = [(query_coverage(question, text), pos) for pos, (text, _) in enumerate(candidates)]
    # Highest coverage first; on ties the earlier (better-ranked) source wins
    ranked = sorted((p for p in scored if p[0] > 0), key=lambda p: (-p[0], p[1]))
    chosen = _pick(candidates, ranked)
    if not chosen:
        # Grounding passed but no sentence overlaps lexically: answer from the top source.
        chosen = [pos for pos, (_, idx) in enumerate(candidates) if idx == candidates[0][1]]
    lines = [f"- {candidates[pos][0]} [{candidates[pos][1]}]" for pos in chosen]
    return "\n".join([INTRO, "", *lines, "", OUTRO])
