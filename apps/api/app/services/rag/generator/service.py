"""Answer generation — OpenAI-compatible LLM when configured; extractive offline."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from typing import Any

from app.core.config import Settings, get_settings
from app.models.enums import LLMPurpose
from app.services.agent.model_router.router import ModelRouter
from app.middleware.metrics import CANCEL_HONORED_TOTAL
from app.services.cancel_registry import get_cancel_registry
from app.services.llm.client import ChatRequest, LLMClient, get_llm_client
from app.services.rag.generator.token_sink import emit_token

logger = logging.getLogger("askflow.generator")

# Naive offline stream chunk size (chars)
OFFLINE_STREAM_STEP = 24
DEFAULT_TEMPERATURE = 0.2
EXTRACTIVE_SOURCE_CAP = 3


class AnswerGenerator:
    """Generate answers from evidence. LLM opt-in; extractive synthesis without keys."""

    def __init__(
        self,
        *,
        llm: LLMClient | None = None,
        router: ModelRouter | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.llm = llm if llm is not None else get_llm_client(self.settings)
        self.router = router or ModelRouter(self.settings)

    async def generate(
        self,
        *,
        question: str,
        sources: list[dict[str, Any]],
        messages: list[dict[str, str]] | None = None,
        cancel_key: str | None = None,
    ) -> str:
        _ = question
        if not sources:
            return ""
        if cancel_key and get_cancel_registry().is_cancelled(cancel_key):
            CANCEL_HONORED_TOTAL.inc()
            return _cancelled_message()
        if self.llm.available and messages:
            try:
                return await self._llm_generate(messages, cancel_key=cancel_key)
            except Exception:
                logger.exception("LLM generate failed; falling back to extractive")
        answer = _extractive(sources)
        await _emit_chunks(answer)
        return answer

    async def stream(
        self,
        *,
        question: str,
        sources: list[dict[str, Any]],
        messages: list[dict[str, str]] | None = None,
    ) -> AsyncIterator[str]:
        _ = question
        if not sources:
            return
        if self.llm.available and messages:
            try:
                async for token in self._llm_stream(messages):
                    yield token
                return
            except Exception:
                logger.exception("LLM stream failed; falling back to extractive chunks")
        answer = _extractive(sources)
        step = OFFLINE_STREAM_STEP
        for i in range(0, len(answer), step):
            yield answer[i : i + step]

    async def _llm_generate(
        self,
        messages: list[dict[str, str]],
        *,
        cancel_key: str | None = None,
    ) -> str:
        """Stream from model (feeds token sink) then join — one LLM call."""
        parts: list[str] = []
        async for token in self._llm_stream(messages):
            if cancel_key and get_cancel_registry().is_cancelled(cancel_key):
                CANCEL_HONORED_TOTAL.inc()
                break
            parts.append(token)
            await emit_token(token)
        text = "".join(parts).strip()
        if not text and cancel_key and get_cancel_registry().is_cancelled(cancel_key):
            return _cancelled_message()
        return text or _fallback_empty()

    async def _llm_stream(self, messages: list[dict[str, str]]) -> AsyncIterator[str]:
        sel = self.router.pick(LLMPurpose.RAG_GENERATE)
        req = ChatRequest(
            model=sel.model,
            messages=messages,
            temperature=DEFAULT_TEMPERATURE,
            max_tokens=self.settings.max_answer_chars,
            stream=True,
        )
        async for token in self.llm.stream(req):
            yield token


async def _emit_chunks(text: str) -> None:
    step = OFFLINE_STREAM_STEP
    for i in range(0, len(text), step):
        await emit_token(text[i : i + step])


def _extractive(sources: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    for s in sources[:EXTRACTIVE_SOURCE_CAP]:
        idx = s.get("index", 1)
        text = str(s.get("text", "")).strip()
        parts.append(f"{text} [{idx}]")
    body = "\n".join(parts)
    return f"根据知识库资料：\n{body}\n\n如需进一步说明，请继续提问。"


def _fallback_empty() -> str:
    return "模型返回为空，请稍后重试或转人工。"


CANCELLED_ANSWER = "生成已取消。"


def _cancelled_message() -> str:
    return CANCELLED_ANSWER
