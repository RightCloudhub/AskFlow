"""Inbox remains available when external mail/SMS are disabled."""

from datetime import UTC, datetime
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter
from pydantic import Field, field_validator

from app.commerce.core.commands import command
from app.commerce.core.deps import MallContext
from app.commerce.core.repository import owned
from app.commerce.core.schemas import Schema
from app.commerce.notify.models import Notification
from app.commerce.notify.service import NotificationService

HOURS_IN_DAY = 24
router = APIRouter()


class Preference(Schema):
    event_type: str
    channel: Literal["email", "sms"]
    enabled: bool = True
    quiet_start: int = Field(default=-1, ge=-1, lt=HOURS_IN_DAY)
    quiet_end: int = Field(default=-1, ge=-1, lt=HOURS_IN_DAY)
    timezone: str = "UTC"

    @field_validator("timezone")
    @classmethod
    def timezone_valid(cls, value):
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as exc:
            raise ValueError("Invalid timezone") from exc
        return value


@router.get("")
async def notifications(ctx: MallContext, cursor: str = ""):
    return await NotificationService(ctx.db).list(ctx.user.id, cursor=cursor)


@router.post("/{notification_id}/read")
async def mark_read(notification_id: str, ctx: MallContext):
    async def perform():
        row = await owned(ctx.db, Notification, owner_id=ctx.user.id, resource_id=notification_id)
        row.read_at = row.read_at or datetime.now(UTC)
        return {"id": row.id, "status": "read"}

    return await command(ctx, "notify.read:" + notification_id, payload={}, action=perform)


@router.put("/preferences")
async def preference(payload: Preference, ctx: MallContext):
    return await command(ctx, "notify.preferences", payload=payload,
                         action=lambda: NotificationService(ctx.db).preference(ctx.user.id, payload))
