"""Mall-only error normalization leaves existing customer-service responses intact."""

from http import HTTPStatus

from fastapi import HTTPException, Request
from fastapi.exception_handlers import http_exception_handler, request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from app.commerce.core.errors import MallError, mall_error_handler
from app.core.trace import get_trace_id


def install_error_handlers(app):
    app.add_exception_handler(MallError, mall_error_handler)
    app.add_exception_handler(RequestValidationError, validation_handler)
    app.add_exception_handler(HTTPException, http_handler)
    app.add_exception_handler(IntegrityError, integrity_handler)


async def integrity_handler(request: Request, exc: IntegrityError):
    if not _mall_request(request):
        raise exc
    return JSONResponse(status_code=HTTPStatus.CONFLICT, content={"code": "constraint_conflict",
        "message": "Request conflicts with existing state", "trace_id": get_trace_id() or ""})


def _mall_request(request):
    return "/mall/" in request.url.path or request.url.path.endswith("/admin/infra")


async def validation_handler(request: Request, exc: RequestValidationError):
    if not _mall_request(request):
        return await request_validation_exception_handler(request, exc)
    return JSONResponse(status_code=HTTPStatus.UNPROCESSABLE_ENTITY, content={"code": "validation_error",
        "message": "Invalid request", "trace_id": get_trace_id() or ""})


async def http_handler(request: Request, exc: HTTPException):
    if not _mall_request(request):
        return await http_exception_handler(request, exc)
    return JSONResponse(status_code=exc.status_code, content={
        "code": "request_rejected", "message": "Request rejected", "trace_id": get_trace_id() or ""})
