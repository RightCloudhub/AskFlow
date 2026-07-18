"""WeCom bot webhook."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse, PlainTextResponse

from app.core.deps import DbSession
from app.services.channels.wecom.service import WeComService

router = APIRouter()
HTTP_BAD = 400
HTTP_FORBIDDEN = 403


@router.get("/events")
async def wecom_verify(request: Request, db: DbSession) -> Response:
    q = dict(request.query_params)
    result = await WeComService(db).handle_payload({}, query=q)
    if result.kind == "echo" and result.echo_str:
        return PlainTextResponse(result.echo_str)
    return PlainTextResponse("forbidden", status_code=HTTP_FORBIDDEN)


@router.post("/events")
async def wecom_events(request: Request, db: DbSession) -> Response:
    try:
        body: dict[str, Any] = await request.json()
    except Exception:
        return JSONResponse({"errcode": HTTP_BAD, "errmsg": "invalid_json"}, status_code=HTTP_BAD)
    q = dict(request.query_params)
    result = await WeComService(db).handle_payload(body, query=q)
    if result.kind == "echo" and result.echo_str:
        return PlainTextResponse(result.echo_str)
    if result.kind == "message":
        from app.core.config import get_settings

        out: dict[str, Any] = {
            "errcode": 0,
            "errmsg": "ok",
            "run_id": result.run_id,
            "route": result.route,
        }
        if get_settings().env in {"test", "development"}:
            out["reply_text"] = result.reply_text
        return JSONResponse(out)
    if result.reply_status == "bad_token":
        return JSONResponse(
            {"errcode": HTTP_FORBIDDEN, "errmsg": "bad_token"},
            status_code=HTTP_FORBIDDEN,
        )
    return JSONResponse({"errcode": 0, "errmsg": "ignored"})
