"""Public web widget API (PRD E7a / U-11)."""

from __future__ import annotations

from fastapi import APIRouter, status
from pydantic import BaseModel, Field

from app.core.deps import CurrentUser, DbSession
from app.middleware.metrics import CHAT_TURNS
from app.schemas.chat import MessageOut
from app.services.chat.session.service import ChatService
from app.services.widget.service import WidgetService

router = APIRouter()

MSG_MAX = 2000


class SessionIn(BaseModel):
    visitor_key: str | None = Field(default=None, max_length=64)
    title: str = Field(default="官网咨询", max_length=40)
    origin: str | None = Field(default=None, max_length=256)


class SessionOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    conversation_id: str
    visitor_key: str
    user_id: str


class WidgetMessageIn(BaseModel):
    content: str = Field(min_length=1, max_length=MSG_MAX)


class WidgetMessageOut(BaseModel):
    user_message: MessageOut
    assistant_message: MessageOut
    run_id: str
    route: str
    intent: str | None = None


@router.post("/session", response_model=SessionOut, status_code=status.HTTP_201_CREATED)
async def open_widget_session(body: SessionIn, db: DbSession) -> SessionOut:
    """Anonymous visitor bootstrap — no prior login required."""
    session = await WidgetService(db).open_session(
        visitor_key=body.visitor_key,
        title=body.title,
        origin=body.origin,
    )
    return SessionOut(
        access_token=session.access_token,
        conversation_id=session.conversation_id,
        visitor_key=session.visitor_key,
        user_id=session.user_id,
    )


@router.get("/conversations/{conversation_id}/messages", response_model=list[MessageOut])
async def widget_list_messages(
    conversation_id: str,
    user: CurrentUser,
    db: DbSession,
) -> list[MessageOut]:
    rows = await ChatService(db).list_messages(conversation_id, user.id)
    return [MessageOut.model_validate(r) for r in rows]


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=WidgetMessageOut,
)
async def widget_send_message(
    conversation_id: str,
    body: WidgetMessageIn,
    user: CurrentUser,
    db: DbSession,
) -> WidgetMessageOut:
    """Same pipeline as main chat — handoff/ticket side-effects apply."""
    user_msg, asst_msg, result = await ChatService(db).handle_user_message(
        conversation_id, user.id, body.content
    )
    CHAT_TURNS.labels(route=result.route, intent=result.intent or "none").inc()
    return WidgetMessageOut(
        user_message=MessageOut.model_validate(user_msg),
        assistant_message=MessageOut.model_validate(asst_msg),
        run_id=result.run_id,
        route=result.route,
        intent=result.intent,
    )
