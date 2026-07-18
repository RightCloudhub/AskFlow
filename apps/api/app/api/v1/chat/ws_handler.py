"""WebSocket chat session: auth, loop, token-buffered turn emission."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from fastapi import WebSocket

from app.api.v1.chat.ws_stream import (
    emit_answer_tokens,
    emit_side_effects,
    message_end_payload,
)
from app.core.security import decode_access_token
from app.middleware.metrics import CANCEL_REQUESTS_TOTAL, CHAT_TURNS
from app.models.user import User
from app.services.cancel_registry import get_cancel_registry
from app.services.chat.session.service import ChatService
from app.services.rag.generator.token_sink import reset_token_sink, set_token_sink

WS_CLOSE_BAD_JSON = 4400
WS_CLOSE_AUTH = 4401


@dataclass
class WsTurn:
    websocket: WebSocket
    db: Any
    user: User
    msg: dict


@dataclass
class WsEmit:
    websocket: WebSocket
    user_msg: Any
    asst_msg: Any
    result: Any
    emitted: list[str]


async def authenticate(websocket: WebSocket, db: Any) -> User | None:
    raw = await websocket.receive_text()
    try:
        frame = json.loads(raw)
    except json.JSONDecodeError:
        await websocket.send_json({"type": "error", "code": "bad_json", "message": "Invalid JSON"})
        await websocket.close(code=WS_CLOSE_BAD_JSON)
        return None
    if frame.get("type") != "auth" or not frame.get("token"):
        await websocket.send_json({"type": "error", "code": "auth_required", "message": "Send auth first"})
        await websocket.close(code=WS_CLOSE_AUTH)
        return None
    try:
        payload = decode_access_token(str(frame["token"]))
        user_id = payload.get("sub")
    except ValueError:
        await websocket.send_json({"type": "error", "code": "invalid_token", "message": "Invalid token"})
        await websocket.close(code=WS_CLOSE_AUTH)
        return None
    user = await db.get(User, user_id)
    if user is None or not user.is_active:
        await websocket.send_json({"type": "error", "code": "invalid_user", "message": "User not found"})
        await websocket.close(code=WS_CLOSE_AUTH)
        return None
    return user


async def session_loop(websocket: WebSocket, db: Any, user: User) -> None:
    while True:
        raw = await websocket.receive_text()
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            await websocket.send_json({"type": "error", "code": "bad_json", "message": "Invalid JSON"})
            continue
        mtype = msg.get("type")
        if mtype == "ping":
            await websocket.send_json({"type": "pong"})
            continue
        if mtype == "cancel":
            await _handle_cancel(msg)
            await websocket.send_json({"type": "message_end", "cancelled": True})
            continue
        if mtype != "message":
            await websocket.send_json({"type": "error", "code": "unknown_type", "message": mtype})
            continue
        await handle_message(WsTurn(websocket=websocket, db=db, user=user, msg=msg))


async def _handle_cancel(msg: dict) -> None:
    """Register cancel for conversation (and optional run_id) — multi-worker via Redis."""
    reg = get_cancel_registry()
    conv = msg.get("conversation_id")
    run_id = msg.get("run_id")
    if conv:
        reg.request_cancel(str(conv))
        CANCEL_REQUESTS_TOTAL.labels(scope="conversation").inc()
    if run_id:
        reg.request_cancel(str(run_id))
        CANCEL_REQUESTS_TOTAL.labels(scope="run").inc()


async def handle_message(turn: WsTurn) -> None:
    parsed = await _validate_message(turn.websocket, turn.msg)
    if parsed is None:
        return
    conversation_id, content = parsed
    emitted: list[str] = []

    async def on_token(chunk: str) -> None:
        emitted.append(chunk)

    sink_token = set_token_sink(on_token)
    try:
        user_msg, asst_msg, result = await ChatService(turn.db).handle_user_message(
            conversation_id, turn.user.id, content
        )
        await turn.db.commit()
    finally:
        reset_token_sink(sink_token)
    await emit_turn(
        WsEmit(
            websocket=turn.websocket,
            user_msg=user_msg,
            asst_msg=asst_msg,
            result=result,
            emitted=emitted,
        )
    )


async def _validate_message(websocket: WebSocket, msg: dict) -> tuple[str, str] | None:
    conversation_id = msg.get("conversation_id")
    content = (msg.get("content") or "").strip()
    if not conversation_id or not content:
        await websocket.send_json(
            {"type": "error", "code": "bad_message", "message": "conversation_id and content required"}
        )
        return None
    from app.core.config import get_settings as _gs

    max_chars = _gs().max_question_chars
    if len(content) > max_chars:
        await websocket.send_json(
            {"type": "error", "code": "too_long", "message": f"content exceeds {max_chars} chars"}
        )
        return None
    return str(conversation_id), content


async def emit_turn(emit: WsEmit) -> None:
    """intent → source* → token* → side_effects → message_end."""
    ws, result = emit.websocket, emit.result
    if result.intent:
        await ws.send_json(
            {
                "type": "intent",
                "intent": result.intent,
                "confidence": result.confidence,
                "route": result.route,
            }
        )
    for src in result.sources:
        await ws.send_json({"type": "source", **src})
    if emit.emitted:
        for chunk in emit.emitted:
            await ws.send_json({"type": "token", "content": chunk})
    else:
        await emit_answer_tokens(ws.send_json, result.answer or "")
    await emit_side_effects(ws.send_json, result.side_effects or {})
    await ws.send_json(
        message_end_payload(
            asst_msg_id=emit.asst_msg.id,
            user_msg_id=emit.user_msg.id,
            result=result,
        )
    )
    CHAT_TURNS.labels(route=result.route, intent=result.intent or "none").inc()
