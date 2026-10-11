"""Live sinks for WS progressive delivery: sources after grounding, tokens during generate()."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from contextvars import ContextVar, Token
from typing import Any

TokenSink = Callable[[str], Awaitable[None]]

_token_sink: ContextVar[TokenSink | None] = ContextVar("askflow_token_sink", default=None)


def set_token_sink(sink: TokenSink | None) -> Token:
    return _token_sink.set(sink)


def reset_token_sink(token: Token) -> None:
    _token_sink.reset(token)


async def emit_token(chunk: str) -> None:
    sink = _token_sink.get()
    if sink is None or not chunk:
        return
    await sink(chunk)


SourcesSink = Callable[[list[dict[str, Any]]], Awaitable[None]]
_sources_sink: ContextVar[SourcesSink | None] = ContextVar("askflow_sources_sink", default=None)


def set_sources_sink(sink: SourcesSink | None) -> Token:
    """Receive grounded sources the moment retrieval passes, before generation starts."""
    return _sources_sink.set(sink)


def reset_sources_sink(token: Token) -> None:
    _sources_sink.reset(token)


async def emit_sources(sources: list[dict[str, Any]]) -> None:
    sink = _sources_sink.get()
    if sink is not None:
        await sink(sources)
