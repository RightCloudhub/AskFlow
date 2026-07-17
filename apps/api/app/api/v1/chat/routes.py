"""Chat REST + WebSocket (PRD §4.5)."""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from pydantic import BaseModel, Field

from app.core.deps import CurrentUser, DbSession
from app.core.security import decode_access_token
from app.middleware.metrics import CHAT_TURNS, WS_CONNECTIONS
from app.models.user import User
from app.schemas.chat import (
    ConversationCreate,
    ConversationOut,
    ConversationUpdate,
    FeedbackOut,
    FeedbackUpsert,
    MessageOut,
)
from app.services.chat.session.service import ChatService
from sqlalchemy import select
from app.models.feedback import Feedback
from app.core import database as dbmod

router = APIRouter()


class SendMessageRequest(BaseModel):
    content: str = Field(min_length=1, max_length=2000)


class SendMessageResponse(BaseModel):
    user_message: MessageOut
    assistant_message: MessageOut
    run_id: str
    route: str
    intent: str | None = None


@router.post("/conversations", response_model=ConversationOut, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    payload: ConversationCreate,
    user: CurrentUser,
    db: DbSession,
) -> ConversationOut:
    conv = await ChatService(db).create_conversation(user.id, payload)
    return ConversationOut.model_validate(conv)


@router.get("/conversations", response_model=list[ConversationOut])
async def list_conversations(user: CurrentUser, db: DbSession) -> list[ConversationOut]:
    rows = await ChatService(db).list_conversations(user.id)
    return [ConversationOut.model_validate(r) for r in rows]


@router.get("/conversations/{conversation_id}", response_model=ConversationOut)
async def get_conversation(
    conversation_id: str, user: CurrentUser, db: DbSession
) -> ConversationOut:
    conv = await ChatService(db).get_conversation(conversation_id, user.id)
    return ConversationOut.model_validate(conv)


@router.patch("/conversations/{conversation_id}", response_model=ConversationOut)
async def update_conversation(
    conversation_id: str,
    payload: ConversationUpdate,
    user: CurrentUser,
    db: DbSession,
) -> ConversationOut:
    conv = await ChatService(db).update_conversation(conversation_id, user.id, payload)
    return ConversationOut.model_validate(conv)


@router.get("/conversations/{conversation_id}/messages", response_model=list[MessageOut])
async def list_messages(
    conversation_id: str, user: CurrentUser, db: DbSession
) -> list[MessageOut]:
    rows = await ChatService(db).list_messages(conversation_id, user.id)
    return [MessageOut.model_validate(r) for r in rows]


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=SendMessageResponse,
)
async def send_message(
    conversation_id: str,
    payload: SendMessageRequest,
    user: CurrentUser,
    db: DbSession,
) -> SendMessageResponse:
    """REST fallback for message turn (WS is preferred for streaming)."""
    user_msg, asst_msg, result = await ChatService(db).handle_user_message(
        conversation_id, user.id, payload.content
    )
    CHAT_TURNS.labels(route=result.route, intent=result.intent or "none").inc()
    return SendMessageResponse(
        user_message=MessageOut.model_validate(user_msg),
        assistant_message=MessageOut.model_validate(asst_msg),
        run_id=result.run_id,
        route=result.route,
        intent=result.intent,
    )


@router.put(
    "/messages/{message_id}/feedback",
    response_model=FeedbackOut,
)
async def upsert_feedback(
    message_id: str,
    payload: FeedbackUpsert,
    user: CurrentUser,
    db: DbSession,
) -> FeedbackOut:
    result = await db.execute(
        select(Feedback).where(Feedback.message_id == message_id, Feedback.user_id == user.id)
    )
    row = result.scalar_one_or_none()
    if row is None:
        row = Feedback(
            message_id=message_id,
            user_id=user.id,
            rating=payload.rating,
            comment=payload.comment,
        )
        db.add(row)
    else:
        row.rating = payload.rating
        row.comment = payload.comment
    await db.flush()
    await db.refresh(row)
    return FeedbackOut.model_validate(row)


@router.websocket("/ws")
async def chat_ws(websocket: WebSocket) -> None:
    """WS protocol: auth first, then message / cancel / ping (PRD §4.5.2)."""
    await websocket.accept()
    WS_CONNECTIONS.inc()
    user: User | None = None
    try:
        # wait for auth frame
        raw = await websocket.receive_text()
        try:
            frame = json.loads(raw)
        except json.JSONDecodeError:
            await websocket.send_json({"type": "error", "code": "bad_json", "message": "Invalid JSON"})
            await websocket.close(code=4400)
            return

        if frame.get("type") != "auth" or not frame.get("token"):
            await websocket.send_json({"type": "error", "code": "auth_required", "message": "Send auth first"})
            await websocket.close(code=4401)
            return

        try:
            payload = decode_access_token(str(frame["token"]))
            user_id = payload.get("sub")
        except ValueError:
            await websocket.send_json({"type": "error", "code": "invalid_token", "message": "Invalid token"})
            await websocket.close(code=4401)
            return

        async with dbmod.SessionLocal() as db:
            user = await db.get(User, user_id)
            if user is None or not user.is_active:
                await websocket.send_json({"type": "error", "code": "invalid_user", "message": "User not found"})
                await websocket.close(code=4401)
                return
            await websocket.send_json({"type": "auth_ok", "user_id": user.id})

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
                    await websocket.send_json({"type": "message_end", "cancelled": True})
                    continue
                if mtype != "message":
                    await websocket.send_json({"type": "error", "code": "unknown_type", "message": mtype})
                    continue

                conversation_id = msg.get("conversation_id")
                content = (msg.get("content") or "").strip()
                if not conversation_id or not content:
                    await websocket.send_json(
                        {"type": "error", "code": "bad_message", "message": "conversation_id and content required"}
                    )
                    continue
                from app.core.config import get_settings as _gs

                max_chars = _gs().max_question_chars
                if len(content) > max_chars:
                    await websocket.send_json(
                        {
                            "type": "error",
                            "code": "too_long",
                            "message": f"content exceeds {max_chars} chars",
                        }
                    )
                    continue

                user_msg, asst_msg, result = await ChatService(db).handle_user_message(
                    conversation_id, user.id, content
                )
                await db.commit()

                if result.intent:
                    await websocket.send_json(
                        {
                            "type": "intent",
                            "intent": result.intent,
                            "confidence": result.confidence,
                            "route": result.route,
                        }
                    )
                for src in result.sources:
                    await websocket.send_json({"type": "source", **src})

                # stream tokens in chunks
                step = 32
                text = result.answer or ""
                for i in range(0, len(text), step):
                    await websocket.send_json({"type": "token", "content": text[i : i + step]})

                if result.side_effects.get("ticket"):
                    await websocket.send_json({"type": "ticket", **result.side_effects["ticket"]})
                if result.side_effects.get("handoff"):
                    await websocket.send_json({"type": "handoff", **result.side_effects["handoff"]})

                await websocket.send_json(
                    {
                        "type": "message_end",
                        "message_id": asst_msg.id,
                        "user_message_id": user_msg.id,
                        "run_id": result.run_id,
                        "trace_id": result.trace_id,
                        "route": result.route,
                        "intent": result.intent,
                        "sources": result.sources,
                        "verification": result.verification,
                        "answer_confidence": result.answer_confidence,
                        "flags": result.flags,
                        "refused": result.refused,
                    }
                )
                CHAT_TURNS.labels(route=result.route, intent=result.intent or "none").inc()

    except WebSocketDisconnect:
        pass
    finally:
        WS_CONNECTIONS.dec()
