"""Optional layered mall limits; validated identity and trusted proxy IP only."""

from fastapi import status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.commerce.core.constants import SECONDS_PER_MINUTE
from app.commerce.infra.errors import dependency_errors
from app.commerce.infra.metrics import LIMIT_TOTAL
from app.commerce.infra.runtime import infra
from app.core.config import get_settings
from app.core.security import decode_access_token
from app.core.trace import get_trace_id
from app.middleware.rate_limit import client_ip

ENDPOINT_COMPONENTS = 6


class MallLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        settings = get_settings()
        if not settings.mall_rate_limit_enabled or "/mall/" not in request.url.path:
            return await call_next(request)
        scopes = self._scopes(request, settings)
        try:
            for scope, key, limit in scopes:
                allowed = await infra().limits.allow(key, limit=limit, window=SECONDS_PER_MINUTE)
                if not allowed:
                    LIMIT_TOTAL.labels(scope=scope).inc()
                    return self._rejected(status.HTTP_429_TOO_MANY_REQUESTS, "rate_limit_exceeded")
        except dependency_errors():
            return self._rejected(status.HTTP_503_SERVICE_UNAVAILABLE, "rate_limiter_unavailable")
        return await call_next(request)

    def _scopes(self, request, settings):
        limit, path = settings.mall_rate_per_minute, request.url.path
        endpoint = request.method + ":" + "/".join(path.split("/")[:ENDPOINT_COMPONENTS])
        scopes = [("global", "global", settings.mall_global_rate_per_minute),
                  ("ip", "ip:" + client_ip(request), limit),
                  ("endpoint", "endpoint:" + client_ip(request) + ":" + endpoint, limit)]
        identity = self._identity(request)
        if identity:
            scopes.append(("user", "user:" + identity, limit))
        if "/flash-sales/" in path and request.method == "POST":
            scopes.append(("flash", "flash:" + (identity or client_ip(request)),
                           settings.mall_flash_rate_per_minute))
        return scopes

    def _identity(self, request):
        token = request.headers.get("authorization", "").removeprefix("Bearer ")
        try:
            return decode_access_token(token).get("sub", "")
        except ValueError:
            return ""

    def _rejected(self, status_code, code):
        return JSONResponse(status_code=status_code, content={
            "code": code, "message": code.replace("_", " "), "trace_id": get_trace_id() or ""},
            headers={"Retry-After": str(SECONDS_PER_MINUTE)})
