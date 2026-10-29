"""Versioned notification templates and safe delivery metadata."""

from typing import Literal

from fastapi import APIRouter
from pydantic import Field
from sqlalchemy import select

from app.commerce.admin.permissions import require
from app.commerce.core.commands import command
from app.commerce.core.constants import NAME_SIZE, PAGE_SIZE
from app.commerce.core.errors import MallError
from app.commerce.core.schemas import Schema, view
from app.commerce.notify.models import NotificationDelivery, NotificationTemplate

BODY_LIMIT = 10000
NOTIFY_WRITE = require("notify:write")

router = APIRouter()


class Template(Schema):
    event_type: str = Field(max_length=NAME_SIZE)
    locale: Literal["zh-CN", "en-US"] = "zh-CN"
    subject: str = Field(max_length=NAME_SIZE)
    body: str = Field(max_length=BODY_LIMIT)
    channels: list[Literal["email", "sms"]] = Field(default_factory=list)
    expected_version: int = Field(default=0, ge=0)


@router.post("/templates")
async def template(payload: Template, ctx=NOTIFY_WRITE):
    async def perform():
        prior = await ctx.db.scalar(select(NotificationTemplate).where(
            NotificationTemplate.event_type == payload.event_type, NotificationTemplate.locale == payload.locale)
            .order_by(NotificationTemplate.version.desc()).limit(1).with_for_update())
        version = prior.version if prior else 0
        if version != payload.expected_version:
            raise MallError("version_conflict")
        row = NotificationTemplate(**payload.model_dump(exclude={"expected_version"}), version=version + 1)
        ctx.db.add(row)
        await ctx.db.flush()
        return {"id": row.id, "version": row.version}

    return await command(ctx, "notify.template", payload=payload, action=perform)


@router.get("/deliveries")
async def deliveries(cursor: str = "", ctx=NOTIFY_WRITE):
    rows = list(await ctx.db.scalars(select(NotificationDelivery).where(NotificationDelivery.id > cursor)
        .order_by(NotificationDelivery.id).limit(PAGE_SIZE)))
    return {"items": [view(row, ("id", "channel", "status", "attempts", "last_error")) for row in rows],
            "next_cursor": rows[-1].id if len(rows) == PAGE_SIZE else None}
