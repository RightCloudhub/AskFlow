"""JSON domain request records contain identifiers, never request bodies or credentials."""

import json
import logging
import re
import time

from starlette.middleware.base import BaseHTTPMiddleware

from app.commerce.account.crypto import digest
from app.core.trace import get_trace_id

LOGGER_NAME = "askflow.mall.http"
MILLISECONDS = 1000
IDENTIFIER = re.compile(r"/(orders|payment)/([a-f0-9-]{36})(?:/|$)")


def configure():
    logger = logging.getLogger(LOGGER_NAME)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False


class MallRequestLogging(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        started = time.monotonic()
        response = await call_next(request)
        if "/mall/" not in request.url.path:
            return response
        identity = getattr(request.state, "mall_user_id", "")
        record = {"event": "mall.http", "trace_id": get_trace_id(), "method": request.method,
                  "status": response.status_code, "duration_ms": int((time.monotonic() - started) * MILLISECONDS),
                  "user_id_hash": digest("log:" + identity) if identity else None}
        matched = IDENTIFIER.search(request.url.path)
        if matched:
            field = "order_id" if matched.group(1) == "orders" else "payment_id"
            record[field] = matched.group(2)
        logging.getLogger(LOGGER_NAME).info(json.dumps(record))
        return response
