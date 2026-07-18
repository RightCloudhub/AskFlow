"""Process-global embedder singleton (tests must call reset_embedder)."""

from __future__ import annotations

from app.core.config import Settings, get_settings
from app.services.rag.embedding.client import Embedder, settings_embedder

_embedder: Embedder | None = None


def get_embedder(settings: Settings | None = None) -> Embedder:
    global _embedder
    if _embedder is None:
        _embedder = settings_embedder(settings or get_settings())
    return _embedder


def reset_embedder(embedder: Embedder | None = None) -> None:
    """Test helper: clear or inject embedder."""
    global _embedder
    _embedder = embedder
