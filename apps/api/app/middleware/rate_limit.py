"""Simple in-process IP rate limiter (PRD L1 / pilot).

Not a multi-worker distributed limiter — Redis can replace later.
Test env is skipped so suite is not flaky.
"""

from __future__ import annotations

import time
from collections import defaultdict, deque

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.config import get_settings

# Paths that must stay reachable for probes / scrape (ops network isolation still required)
SKIP_PREFIXES = (
    "/health",
    "/metrics",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/",
)
WINDOW_SEC = 60


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app) -> None:  # type: ignore[no-untyped-def]
        super().__init__(app)
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def _client_key(self, request: Request) -> str:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        if request.client and request.client.host:
            return request.client.host
        return "unknown"

    def _should_skip(self, path: str) -> bool:
        if path in {"/", "/health", "/metrics"}:
            return True
        for p in SKIP_PREFIXES:
            if p != "/" and path.startswith(p):
                return True
        return False

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        settings = get_settings()
        if settings.env == "test":
            return await call_next(request)
        path = request.url.path
        # strip api prefix variants
        if self._should_skip(path) or path.endswith("/health") or path.endswith("/metrics"):
            return await call_next(request)

        limit = max(1, int(settings.rate_limit_per_minute))
        key = self._client_key(request)
        now = time.time()
        bucket = self._hits[key]
        while bucket and (now - bucket[0]) > WINDOW_SEC:
            bucket.popleft()
        if len(bucket) >= limit:
            return JSONResponse(
                status_code=429,
                content={"detail": "rate_limit_exceeded", "limit_per_minute": limit},
                headers={"Retry-After": "60"},
            )
        bucket.append(now)
        return await call_next(request)
