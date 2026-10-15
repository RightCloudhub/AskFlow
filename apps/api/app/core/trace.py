"""Request-scoped trace id shared by middleware, turns and audit rows (arch §4.12)."""

import contextvars

_trace_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "askflow_trace_id", default=None
)


def set_trace_id(value: str) -> None:
    _trace_id.set(value)


def get_trace_id() -> str | None:
    return _trace_id.get()
