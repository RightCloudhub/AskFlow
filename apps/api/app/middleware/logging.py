"""Request logging with trace_id."""

from __future__ import annotations

import logging
import time
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("askflow.http")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        trace_id = request.headers.get("x-trace-id") or f"tr_{uuid4().hex[:12]}"
        request.state.trace_id = trace_id
        start = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start) * 1000
        response.headers["X-Trace-Id"] = trace_id
        logger.info(
            "method=%s path=%s status=%s duration_ms=%.1f trace_id=%s",
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
            trace_id,
        )
        return response
