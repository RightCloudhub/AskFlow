"""DingTalk bot webhook."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.core.deps import DbSession
from app.services.channels.dingtalk.service import DingTalkService

router = APIRouter()
HTTP_BAD = 400
HTTP_FORBIDDEN = 403


@router.post("/events")
async def dingtalk_events(request: Request, db: DbSession) -> JSONResponse:
    try:
        body: dict[str, Any] = await request.json()
    except Exception:
        return JSONResponse({"code": HTTP_BAD, "msg": "invalid_json"}, status_code=HTTP_BAD)
    headers = {k: v for k, v in request.headers.items()}
    result = await DingTalkService(db).handle_payload(body, headers=headers)
    if result.kind == "challenge":
        return JSONResponse({"challenge": result.challenge})
    if result.kind == "message":
        from app.core.config import get_settings

        out: dict[str, Any] = {
            "msgtype": "text",
            "text": {"content": result.reply_text or ""},
            "run_id": result.run_id,
            "route": result.route,
        }
        if get_settings().env not in {"test", "development"}:
            # production: still return robot response shape
            out = {"msgtype": "text", "text": {"content": result.reply_text or ""}}
        return JSONResponse(out)
    if result.reply_status == "bad_token":
        return JSONResponse({"code": HTTP_FORBIDDEN, "msg": "bad_token"}, status_code=HTTP_FORBIDDEN)
    return JSONResponse({"code": 0, "msg": "ignored"})
