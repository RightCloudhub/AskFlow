"""Admin user management + data export/delete (PRD E9 / E13 / §12.2)."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation, Message
from app.models.feedback import Feedback
from app.models.ticket import Ticket
from app.models.user import User
from app.services.audit.logger.service import AuditService


class UserAdminService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_users(self) -> list[User]:
        result = await self.db.execute(select(User).order_by(User.created_at.desc()))
        return list(result.scalars().all())

    async def set_active(self, user_id: str, active: bool, *, actor_id: str) -> User:
        user = await self.db.get(User, user_id)
        if user is None:
            raise HTTPException(status_code=404, detail="User not found")
        user.is_active = active
        await self.db.flush()
        await AuditService(self.db).log(
            action="user.disable" if not active else "user.enable",
            resource_type="user",
            resource_id=user_id,
            actor_id=actor_id,
            detail={"is_active": active},
        )
        await self.db.refresh(user)
        return user

    async def export_user_data(self, user_id: str) -> dict[str, Any]:
        user = await self.db.get(User, user_id)
        if user is None:
            raise HTTPException(status_code=404, detail="User not found")
        convs = await self.db.execute(
            select(Conversation).where(Conversation.user_id == user_id)
        )
        conversations = list(convs.scalars().all())
        conv_ids = [c.id for c in conversations]
        messages: list[Message] = []
        if conv_ids:
            msg_r = await self.db.execute(
                select(Message).where(Message.conversation_id.in_(conv_ids))
            )
            messages = list(msg_r.scalars().all())
        tickets = await self.db.execute(select(Ticket).where(Ticket.user_id == user_id))
        feedbacks = await self.db.execute(select(Feedback).where(Feedback.user_id == user_id))
        return {
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "role": user.role,
                "is_active": user.is_active,
                "created_at": user.created_at.isoformat() if user.created_at else None,
            },
            "conversations": [
                {"id": c.id, "title": c.title, "status": c.status} for c in conversations
            ],
            "messages": [
                {
                    "id": m.id,
                    "conversation_id": m.conversation_id,
                    "role": m.role,
                    "content": m.content,
                }
                for m in messages
            ],
            "tickets": [
                {"id": t.id, "title": t.title, "status": t.status} for t in tickets.scalars().all()
            ],
            "feedbacks": [
                {"id": f.id, "message_id": f.message_id, "rating": f.rating}
                for f in feedbacks.scalars().all()
            ],
        }

    async def delete_user_data(self, user_id: str, *, actor_id: str) -> dict[str, int]:
        """GDPR-style delete: remove messages/convs/tickets/feedback; disable user."""
        user = await self.db.get(User, user_id)
        if user is None:
            raise HTTPException(status_code=404, detail="User not found")

        convs = await self.db.execute(
            select(Conversation).where(Conversation.user_id == user_id)
        )
        conversations = list(convs.scalars().all())
        n_msg = 0
        for c in conversations:
            msg_r = await self.db.execute(
                select(Message).where(Message.conversation_id == c.id)
            )
            for m in msg_r.scalars().all():
                await self.db.delete(m)
                n_msg += 1
            await self.db.delete(c)

        tickets = await self.db.execute(select(Ticket).where(Ticket.user_id == user_id))
        n_ticket = 0
        for t in tickets.scalars().all():
            await self.db.delete(t)
            n_ticket += 1

        fbs = await self.db.execute(select(Feedback).where(Feedback.user_id == user_id))
        n_fb = 0
        for f in fbs.scalars().all():
            await self.db.delete(f)
            n_fb += 1

        user.is_active = False
        user.email = f"deleted+{user.id[:8]}@invalid.local"
        user.username = f"deleted_{user.id[:8]}"
        await self.db.flush()
        await AuditService(self.db).log(
            action="user.data_delete",
            resource_type="user",
            resource_id=user_id,
            actor_id=actor_id,
            detail={"messages": n_msg, "tickets": n_ticket, "feedbacks": n_fb},
        )
        return {"messages": n_msg, "conversations": len(conversations), "tickets": n_ticket, "feedbacks": n_fb}
