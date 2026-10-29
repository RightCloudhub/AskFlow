"""Stable business errors; security counters can explicitly commit on rejection."""

from http import HTTPStatus

from fastapi import Request
from fastapi.responses import JSONResponse

from app.core.trace import get_trace_id


class MallError(Exception):
    def __init__(self, code: str, *, status: int = HTTPStatus.CONFLICT, persist: bool = False):
        self.code, self.status, self.persist = code, status, persist
        super().__init__(code)


async def mall_error_handler(request: Request, exc: MallError):
    return JSONResponse(
        status_code=exc.status,
        content={"code": exc.code, "message": exc.code.replace("_", " "),
                 "trace_id": get_trace_id() or request.headers.get("x-trace-id", "")},
    )
