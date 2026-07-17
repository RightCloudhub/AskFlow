"""Process-wide AppContext (set at create_app / load_plugins)."""

from __future__ import annotations

from app.plugins.context import AppContext

_CTX: AppContext | None = None


def set_app_context(ctx: AppContext | None) -> None:
    global _CTX
    _CTX = ctx


def get_app_context() -> AppContext | None:
    return _CTX


def require_app_context() -> AppContext:
    if _CTX is None:
        raise RuntimeError("AppContext not loaded; call load_plugins first")
    return _CTX
