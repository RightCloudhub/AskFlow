"""Cross-worker cancel registry (PRD E12): process-local + optional Redis)."""

from __future__ import annotations

import logging
import time
from typing import Any

from app.core.config import Settings, get_settings

logger = logging.getLogger("askflow.cancel")

# Cancel keys expire so stale flags do not stick forever
DEFAULT_TTL_SEC = 300
REDIS_KEY_PREFIX = "askflow:cancel:"


class CancelRegistry:
    """Request/observe cancel by conversation_id or run_id."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._local: dict[str, float] = {}
        self._ttl = float(self.settings.cancel_ttl_seconds)

    def request_cancel(self, key: str) -> None:
        if not key:
            return
        deadline = time.time() + self._ttl
        self._local[key] = deadline
        self._redis_set(key, self._ttl)
        logger.info("cancel requested key=%s", key)

    def is_cancelled(self, key: str) -> bool:
        if not key:
            return False
        if self._local_hit(key):
            return True
        return self._redis_hit(key)

    def clear(self, key: str) -> None:
        self._local.pop(key, None)
        self._redis_delete(key)

    def _local_hit(self, key: str) -> bool:
        exp = self._local.get(key)
        if exp is None:
            return False
        if exp < time.time():
            self._local.pop(key, None)
            return False
        return True

    def _redis_set(self, key: str, ttl: float) -> None:
        url = self.settings.redis_url
        if not url:
            return
        try:
            import redis

            client = redis.from_url(url)
            client.setex(f"{REDIS_KEY_PREFIX}{key}", int(ttl), "1")
            client.close()
        except Exception:
            logger.exception("cancel redis set failed")

    def _redis_hit(self, key: str) -> bool:
        url = self.settings.redis_url
        if not url:
            return False
        try:
            import redis

            client = redis.from_url(url)
            val = client.get(f"{REDIS_KEY_PREFIX}{key}")
            client.close()
            return val is not None
        except Exception:
            logger.exception("cancel redis get failed")
            return False

    def _redis_delete(self, key: str) -> None:
        url = self.settings.redis_url
        if not url:
            return
        try:
            import redis

            client = redis.from_url(url)
            client.delete(f"{REDIS_KEY_PREFIX}{key}")
            client.close()
        except Exception:
            logger.exception("cancel redis delete failed")


_registry: CancelRegistry | None = None


def get_cancel_registry(settings: Settings | None = None) -> CancelRegistry:
    global _registry
    if _registry is None:
        _registry = CancelRegistry(settings or get_settings())
    return _registry


def reset_cancel_registry() -> None:
    global _registry
    _registry = None


def cancel_status_payload(keys: list[str]) -> dict[str, Any]:
    reg = get_cancel_registry()
    return {k: reg.is_cancelled(k) for k in keys if k}
