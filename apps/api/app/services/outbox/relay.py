"""Publish pending outbox events: WS broadcast + channel push (arch §4.5 / §10.7)."""

from app.models.conversation import Conversation
from app.services.chat.ws_registry import registry as ws_registry
from app.services.outbound import OutboundDelivery
from app.services.outbound.senders import sender_configured
from app.services.outbox.store import EVENT_CONFIRMATION_REQUESTED, EVENT_TASK_RESULT

PUSH_EVENTS = frozenset({EVENT_TASK_RESULT, EVENT_CONFIRMATION_REQUESTED})
PROACTIVE_TYPE = "proactive"


async def publish_event(db, event, *, delivery: OutboundDelivery | None = None) -> None:
    """Consumers must be idempotent; unknown event types are acknowledged."""
    if event.event_type.startswith("mall."):
        from app.commerce.events import dispatch

        await dispatch(db, event)
        return
    if event.event_type not in PUSH_EVENTS:
        return
    payload = dict(event.payload or {})
    conversation_id = str(payload.get("conversation_id") or "")
    if not conversation_id:
        return
    await ws_registry.broadcast(
        conversation_id, {"type": PROACTIVE_TYPE, "event": event.event_type, **payload}
    )
    await _push_to_channel(db, event, payload, delivery=delivery)


async def _push_to_channel(db, event, payload: dict, *, delivery: OutboundDelivery | None) -> None:
    text = str(payload.get("content") or "")
    if not text:
        return
    target = await _channel_target(db, payload)
    if target is None:
        return
    channel, chat_key = target
    if delivery is None and not sender_configured(channel):
        return  # no push credentials; the session write-back and WS broadcast still apply
    await (delivery or OutboundDelivery()).deliver(
        db, channel=channel, target=chat_key, text=text, event_type=event.event_type
    )


async def _channel_target(db, payload: dict) -> tuple[str, str] | None:
    conversation = await db.get(Conversation, str(payload.get("conversation_id") or ""))
    meta = (conversation.metadata_json or {}) if conversation is not None else {}
    channel, chat_key = meta.get("channel"), meta.get("channel_chat_key")
    if not channel or not chat_key:
        return None
    return str(channel), str(chat_key)
