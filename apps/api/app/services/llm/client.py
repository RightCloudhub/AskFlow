"""OpenAI-compatible chat completions + streaming via httpx (PRD §4.2 generator)."""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

import httpx

from app.core.config import Settings, get_settings
from app.middleware.metrics import LLM_ERROR_TOTAL

logger = logging.getLogger("askflow.llm")

CHAT_PATH = "/v1/chat/completions"
DEFAULT_TIMEOUT_SEC = 60.0
STREAM_READ_TIMEOUT_SEC = 120.0
DEFAULT_TEMPERATURE = 0.2


@dataclass
class ChatRequest:
    model: str
    messages: list[dict[str, str]]
    temperature: float = DEFAULT_TEMPERATURE
    max_tokens: int | None = None
    stream: bool = False


@dataclass
class _StreamCtx:
    client: httpx.AsyncClient
    base_url: str
    headers: dict[str, str]
    body: dict[str, Any]


class LLMClient:
    """Thin OpenAI-compatible client. `available` is False when base_url/key missing."""

    def __init__(
        self,
        *,
        base_url: str | None,
        api_key: str | None,
        timeout: float = DEFAULT_TIMEOUT_SEC,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.base_url = (base_url or "").rstrip("/") or None
        self.api_key = api_key
        self.timeout = timeout
        self._transport = transport

    @property
    def available(self) -> bool:
        return bool(self.base_url and self.api_key)

    async def complete(self, req: ChatRequest) -> str:
        body = _to_payload(req, stream=False)
        data = await self._post_json(body, purpose="complete")
        return _content_from_response(data)

    async def stream(self, req: ChatRequest) -> AsyncIterator[str]:
        body = _to_payload(req, stream=True)
        async for token in self._iter_sse(body):
            yield token

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def _post_json(self, body: dict[str, Any], *, purpose: str) -> dict[str, Any]:
        if not self.available:
            raise RuntimeError("llm_not_configured")
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout,
                transport=self._transport,
            ) as client:
                resp = await client.post(
                    f"{self.base_url}{CHAT_PATH}",
                    headers=self._headers(),
                    json=body,
                )
                resp.raise_for_status()
                return resp.json()
        except Exception as exc:
            LLM_ERROR_TOTAL.labels(purpose=purpose, error_class=type(exc).__name__).inc()
            raise

    async def _iter_sse(self, body: dict[str, Any]) -> AsyncIterator[str]:
        if not self.available:
            raise RuntimeError("llm_not_configured")
        timeout = httpx.Timeout(self.timeout, read=STREAM_READ_TIMEOUT_SEC)
        try:
            async with httpx.AsyncClient(timeout=timeout, transport=self._transport) as client:
                ctx = _StreamCtx(
                    client=client,
                    base_url=self.base_url or "",
                    headers=self._headers(),
                    body=body,
                )
                async for token in _stream_tokens(ctx):
                    yield token
        except Exception as exc:
            LLM_ERROR_TOTAL.labels(purpose="stream", error_class=type(exc).__name__).inc()
            raise


async def _stream_tokens(ctx: _StreamCtx) -> AsyncIterator[str]:
    async with ctx.client.stream(
        "POST",
        f"{ctx.base_url}{CHAT_PATH}",
        headers=ctx.headers,
        json=ctx.body,
    ) as resp:
        resp.raise_for_status()
        async for line in resp.aiter_lines():
            token = _sse_token(line)
            if token is None:
                continue
            if token == "[DONE]":
                return
            yield token


def _to_payload(req: ChatRequest, *, stream: bool) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "model": req.model,
        "messages": req.messages,
        "temperature": req.temperature,
        "stream": stream,
    }
    if req.max_tokens is not None:
        payload["max_tokens"] = req.max_tokens
    return payload


def _content_from_response(data: dict[str, Any]) -> str:
    choices = data.get("choices") or []
    if not choices:
        return ""
    msg = choices[0].get("message") or {}
    return str(msg.get("content") or "")


def _sse_token(line: str) -> str | None:
    if not line or not line.startswith("data:"):
        return None
    payload = line[len("data:") :].strip()
    if payload == "[DONE]":
        return "[DONE]"
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return None
    choices = data.get("choices") or []
    if not choices:
        return None
    delta = choices[0].get("delta") or {}
    content = delta.get("content")
    return str(content) if content else None


_client: LLMClient | None = None


def get_llm_client(settings: Settings | None = None) -> LLMClient:
    global _client
    if _client is None:
        s = settings or get_settings()
        _client = LLMClient(
            base_url=s.llm_base_url,
            api_key=s.llm_api_key,
            timeout=s.llm_timeout_seconds,
        )
    return _client


def reset_llm_client(client: LLMClient | None = None) -> None:
    global _client
    _client = client
