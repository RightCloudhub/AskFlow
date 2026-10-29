"""Event-to-inbox projection is durable and idempotent per recipient/event."""

import json
from datetime import UTC, datetime

from sqlalchemy import func, select

from app.commerce.core.repository import insert_once, owned_page
from app.commerce.core.schemas import view
from app.commerce.notify.models import Notification, NotificationDelivery, NotificationPreference, NotificationTemplate
from app.commerce.notify.templates import render

NOTIFICATION_FIELDS = ("id", "event_type", "subject", "body", "read_at", "created_at")
CHANNELS = ("email", "sms")


class NotificationService:
    def __init__(self, db):
        self.db = db

    async def consume(self, envelope):
        payload = envelope.get("payload", {})
        user_id = payload.get("user_id")
        if not user_id:
            return
        from app.commerce.account.contacts import contact

        recipient = await contact(self.db, user_id)
        if recipient is None:
            return
        template = await self.db.scalar(select(NotificationTemplate).where(
            NotificationTemplate.event_type == envelope["event_type"], NotificationTemplate.active,
            NotificationTemplate.locale == recipient["locale"])
            .order_by(NotificationTemplate.version.desc()).limit(1))
        body = render(template.body, payload) if template else json.dumps(payload, ensure_ascii=False)
        subject = render(template.subject, payload) if template else envelope["event_type"]
        created = await insert_once(self.db, Notification, values={"user_id": user_id,
            "event_id": envelope["event_id"], "event_type": envelope["event_type"],
            "locale": recipient["locale"], "subject": subject, "body": body}, unique=["user_id", "event_id"])
        if not created:
            return
        row = await self.db.scalar(select(Notification).where(Notification.user_id == user_id,
            Notification.event_id == envelope["event_id"]))
        for channel in CHANNELS:
            if template and channel in template.channels:
                await insert_once(self.db, NotificationDelivery, values={"notification_id": row.id,
                    "channel": channel, "next_attempt_at": datetime.now(UTC)}, unique=["notification_id", "channel"])

    async def list(self, user_id: str, *, cursor: str = ""):
        rows, after = await owned_page(self.db, Notification, owner_id=user_id, cursor=cursor)
        unread = await self.db.scalar(select(func.count()).select_from(Notification).where(
            Notification.user_id == user_id, Notification.read_at.is_(None)))
        return {"items": [view(row, NOTIFICATION_FIELDS) for row in rows],
                "next_cursor": after, "unread": unread}

    async def preference(self, user_id: str, payload):
        await insert_once(self.db, NotificationPreference, values={"user_id": user_id,
            **payload.model_dump()}, unique=["user_id", "event_type", "channel"])
        row = await self.db.scalar(select(NotificationPreference).where(
            NotificationPreference.user_id == user_id, NotificationPreference.event_type == payload.event_type,
            NotificationPreference.channel == payload.channel))
        for key, value in payload.model_dump().items():
            setattr(row, key, value)
        row.version += 1
        return {"status": "saved", "version": row.version}
