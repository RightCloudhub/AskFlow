"""Anonymize support records while preserving financial foreign-key references."""

from sqlalchemy import select, update

from app.models.conversation import Conversation, Message
from app.models.handoff import HandoffSession
from app.models.ticket import Ticket


async def anonymize_support(db, user_id: str):
    conversation_ids = select(Conversation.id).where(Conversation.user_id == user_id)
    messages = await db.execute(update(Message).where(Message.conversation_id.in_(conversation_ids))
        .values(content="[deleted]", meta={}))
    conversations = await db.execute(update(Conversation).where(Conversation.user_id == user_id)
        .values(title="[deleted]", metadata_json={}, status="closed"))
    tickets = await db.scalars(select(Ticket).where(Ticket.user_id == user_id))
    count = 0
    for ticket in tickets:
        ticket.title, ticket.description, ticket.content = "deleted_" + ticket.id, "[deleted]", {}
        count += 1
    await db.execute(update(HandoffSession).where(HandoffSession.user_id == user_id).values(summary="[deleted]"))
    return {"messages": messages.rowcount, "conversations": conversations.rowcount, "tickets": count, "feedbacks": 0}
