"""API v1 routers — assembled by plugin loader."""

from fastapi import APIRouter

from app.plugins.context import AppContext
from app.plugins.loader import load_plugins
from app.plugins.runtime import get_app_context


def build_api_router(ctx: AppContext | None = None) -> APIRouter:
    """Return plugin-assembled API router (loads plugins if needed)."""
    if ctx is None:
        existing = get_app_context()
        ctx = existing if existing is not None else load_plugins()
    return ctx.api_router
