"""In-process sliding-window IP rate limiter (PRD L1 / pilot).

Single-process only — a Redis limiter replaces it for multi-worker deployments.
The test env is skipped so the suite is not flaky.
"""

from __future__ import annotations

import time
from collections import defaultdict, deque

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.config import get_settings

WINDOW_SEC = 60
UNKNOWN_CLIENT = "unknown"
# Probe / scrape / docs paths are matched exactly, never by suffix (audit D-16).
SKIP_SUFFIXES = ("/health", "/metrics")
SKIP_EXACT = frozenset({"/", "/docs", "/docs/oauth2-redirect", "/redoc", "/openapi.json"})


def client_ip(request: Request) -> str:
    """Client address; behind ``TRUSTED_PROXY_HOPS`` proxies read XFF from the right (D-03).

    Each trusted proxy appends the address it received the request from, so the entry
    ``hops`` positions from the right is the one the outermost trusted proxy saw. Anything
    to its left is client-controlled.
    """
    settings = get_settings()
    hops = settings.trusted_proxy_hops if settings.trust_proxy_headers else 0
    forwarded = [p.strip() for p in request.headers.get("x-forwarded-for", "").split(",")]
    forwarded = [p for p in forwarded if p]
    if hops and len(forwarded) >= hops:
        return forwarded[-hops]
    if request.client and request.client.host:
        return request.client.host
    return UNKNOWN_CLIENT


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app) -> None:  # type: ignore[no-untyped-def]
        super().__init__(app)
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._last_sweep = time.time()
        prefix = get_settings().api_prefix
        self._skip = SKIP_EXACT | set(SKIP_SUFFIXES) | {prefix + s for s in SKIP_SUFFIXES}

    def _sweep(self, now: float) -> None:
        """Drop idle clients once per window so the key space stays bounded (D-17)."""
        if now - self._last_sweep < WINDOW_SEC:
            return
        idle = [k for k, b in self._hits.items() if not b or now - b[-1] > WINDOW_SEC]
        for key in idle:
            del self._hits[key]
        self._last_sweep = now

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        settings = get_settings()
        if settings.env == "test" or request.url.path in self._skip:
            return await call_next(request)
        now = time.time()
        self._sweep(now)
        limit = max(1, settings.rate_limit_per_minute)
        bucket = self._hits[client_ip(request)]
        while bucket and now - bucket[0] > WINDOW_SEC:
            bucket.popleft()
        if len(bucket) >= limit:
            return JSONResponse(
                status_code=429,
                content={"detail": "rate_limit_exceeded", "limit_per_minute": limit},
                headers={"Retry-After": str(WINDOW_SEC)},
            )
        bucket.append(now)
        return await call_next(request)
