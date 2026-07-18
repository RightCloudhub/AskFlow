"""Optional live token sink for WS progressive delivery during generate()."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from contextvars import ContextVar, Token

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
