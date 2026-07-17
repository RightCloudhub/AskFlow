"""Feishu bot webhook (PRD E7b)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.core.deps import DbSession
from app.services.channels.feishu.service import FeishuService

router = APIRouter()


@router.post("/events")
async def feishu_events(request: Request, db: DbSession) -> JSONResponse:
    """
    Feishu event subscription endpoint.

    - URL verification: returns {\"challenge\": ...}
    - Message events: run Agent pipeline; optional API reply when app credentials set
    """
    try:
        body: dict[str, Any] = await request.json()
    except Exception:
        return JSONResponse({"code": 400, "msg": "invalid_json"}, status_code=400)

    result = await FeishuService(db).handle_payload(body)
    if result.kind == "challenge":
        return JSONResponse({"challenge": result.challenge})
    if result.kind == "message":
        return JSONResponse(
            {
                "code": 0,
                "msg": "ok",
                "run_id": result.run_id,
                "route": result.route,
                "reply_status": result.reply_status,
                # Echo for tests / dry-run when no outbound credentials
                "reply_text": result.reply_text,
            }
        )
    if result.reply_status == "bad_token":
        return JSONResponse({"code": 403, "msg": "bad_token"}, status_code=403)
    return JSONResponse({"code": 0, "msg": "ignored"})
