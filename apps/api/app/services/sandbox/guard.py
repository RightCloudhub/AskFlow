"""Controlled code sandbox gate (PRD E28) — default OFF."""

from __future__ import annotations

from app.core.config import get_settings

SANDBOX_DISABLED_MSG = "sandbox_disabled"


def sandbox_allowed() -> bool:
    return bool(get_settings().sandbox_enabled)


def require_sandbox() -> None:
    """Raise if sandbox tools are invoked while disabled."""
    if not sandbox_allowed():
        raise RuntimeError(SANDBOX_DISABLED_MSG)


def sandbox_status() -> dict[str, object]:
    return {
        "enabled": sandbox_allowed(),
        "note": "Default off; enable SANDBOX_ENABLED=1 only after threat model.",
    }
