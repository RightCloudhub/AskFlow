"""Answer generation — extractive MVP when LLM unavailable; stream-ready interface."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any


class AnswerGenerator:
    """Generate answers from evidence. Uses extractive synthesis without LLM for MVP offline."""

    async def generate(
        self,
        *,
        question: str,
        sources: list[dict[str, Any]],
        messages: list[dict[str, str]] | None = None,
    ) -> str:
        _ = messages
        if not sources:
            return ""
        parts: list[str] = []
        for s in sources[:3]:
            idx = s.get("index", 1)
            text = str(s.get("text", "")).strip()
            parts.append(f"{text} [{idx}]")
        body = "\n".join(parts)
        return f"根据知识库资料：\n{body}\n\n如需进一步说明，请继续提问。"

    async def stream(
        self,
        *,
        question: str,
        sources: list[dict[str, Any]],
        messages: list[dict[str, str]] | None = None,
    ) -> AsyncIterator[str]:
        answer = await self.generate(question=question, sources=sources, messages=messages)
        # naive chunking for WS token frames
        step = 24
        for i in range(0, len(answer), step):
            yield answer[i : i + step]
