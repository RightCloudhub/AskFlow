"""Feishu bot webhook (PRD E7b)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.deps import DbSession
from app.services.channels.feishu.security import FeishuAuthError, FeishuRequest
from app.services.channels.feishu.service import FeishuService

router = APIRouter()
ECHO_REPLY_ENVS = frozenset({"test", "development"})


@router.post("/events")
async def feishu_events(request: Request, db: DbSession) -> JSONResponse:
    """
    Feishu event subscription endpoint.

    - URL verification: returns {"challenge": ...}
    - Message events: signature/replay checked, then the Agent pipeline runs
    """
    raw = FeishuRequest(raw_body=await request.body(), headers=dict(request.headers))
    try:
        result = await FeishuService(db).handle_request(raw)
    except FeishuAuthError as exc:
        return JSONResponse({"code": 403, "msg": str(exc)}, status_code=403)
    except ValueError:
        return JSONResponse({"code": 400, "msg": "invalid_body"}, status_code=400)
    if result.kind == "challenge":
        return JSONResponse({"challenge": result.challenge})
    if result.kind in {"duplicate", "accepted"}:
        return JSONResponse({"code": 0, "msg": result.kind})
    if result.kind != "message":
        return JSONResponse({"code": 0, "msg": "ignored"})
    body_out: dict[str, Any] = {
        "code": 0,
        "msg": "ok",
        "run_id": result.run_id,
        "route": result.route,
        "reply_status": result.reply_status,
    }
    # Never echo the full answer on an open webhook in staging/production
    if get_settings().env in ECHO_REPLY_ENVS:
        body_out["reply_text"] = result.reply_text
    return JSONResponse(body_out)
