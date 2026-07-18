"""In-process TTL retrieval cache (PRD E25 cost optimization)."""

from __future__ import annotations

import hashlib
import threading
import time
from dataclasses import dataclass
from typing import Any

from app.core.config import Settings, get_settings
from app.middleware.metrics import RETRIEVAL_CACHE_TOTAL


@dataclass
class _Entry:
    expires_at: float
    payload: Any


class RetrievalCache:
    """Process-local LRU-ish dict with TTL; multi-worker safe only with sticky routing."""

    def __init__(self, *, ttl_seconds: int, max_entries: int) -> None:
        self.ttl = max(0, int(ttl_seconds))
        self.max_entries = max(1, int(max_entries))
        self._lock = threading.Lock()
        self._data: dict[str, _Entry] = {}

    @property
    def enabled(self) -> bool:
        return self.ttl > 0

    def make_key(self, query: str, top_k: int) -> str:
        raw = f"{top_k}\n{query.strip().lower()}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def get(self, key: str) -> Any | None:
        if not self.enabled:
            return None
        now = time.time()
        with self._lock:
            entry = self._data.get(key)
            if entry is None:
                RETRIEVAL_CACHE_TOTAL.labels(result="miss").inc()
                return None
            if entry.expires_at < now:
                del self._data[key]
                RETRIEVAL_CACHE_TOTAL.labels(result="miss").inc()
                return None
            RETRIEVAL_CACHE_TOTAL.labels(result="hit").inc()
            return entry.payload

    def set(self, key: str, payload: Any) -> None:
        if not self.enabled:
            return
        with self._lock:
            if len(self._data) >= self.max_entries:
                # drop arbitrary oldest-ish: first key
                self._data.pop(next(iter(self._data)), None)
            self._data[key] = _Entry(expires_at=time.time() + self.ttl, payload=payload)

    def clear(self) -> None:
        with self._lock:
            self._data.clear()


_cache: RetrievalCache | None = None


def get_retrieval_cache(settings: Settings | None = None) -> RetrievalCache:
    global _cache
    if _cache is None:
        s = settings or get_settings()
        _cache = RetrievalCache(
            ttl_seconds=s.retrieval_cache_ttl_seconds,
            max_entries=s.retrieval_cache_max_entries,
        )
    return _cache


def reset_retrieval_cache() -> None:
    global _cache
    if _cache is not None:
        _cache.clear()
    _cache = None
