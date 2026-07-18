"""Chat REST + WebSocket (PRD §4.5)."""

from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.api.v1.chat import ws_handler
from app.core import database as dbmod
from app.core.deps import CurrentUser, DbSession
from app.middleware.metrics import WS_CONNECTIONS
from app.models.feedback import Feedback
from app.schemas.chat import (
    ConversationCreate,
    ConversationOut,
    ConversationUpdate,
    FeedbackOut,
    FeedbackUpsert,
    MessageOut,
)
from app.services.chat.session.service import ChatService

router = APIRouter()


class SendMessageRequest(BaseModel):
    content: str = Field(min_length=1, max_length=2000)
    attachments: list[dict] | None = None
    bot_id: str | None = None
    locale: str | None = None


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
    from app.middleware.metrics import CHAT_TURNS

    user_msg, asst_msg, result = await ChatService(db).handle_user_message(
        conversation_id,
        user.id,
        payload.content,
        attachments=payload.attachments,
        bot_id=payload.bot_id,
        locale=payload.locale,
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
    try:
        async with dbmod.SessionLocal() as db:
            user = await ws_handler.authenticate(websocket, db)
            if user is None:
                return
            await websocket.send_json({"type": "auth_ok", "user_id": user.id})
            await ws_handler.session_loop(websocket, db, user)
    except WebSocketDisconnect:
        pass
    finally:
        WS_CONNECTIONS.dec()
