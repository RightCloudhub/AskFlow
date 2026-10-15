"""ID helpers."""

from __future__ import annotations

import uuid


def new_id() -> str:
    return str(uuid.uuid4())


def new_run_id() -> str:
    return f"run_{uuid.uuid4().hex[:16]}"


def new_trace_id() -> str:
    from app.core.trace import get_trace_id

    return get_trace_id() or f"tr_{uuid.uuid4().hex[:16]}"
