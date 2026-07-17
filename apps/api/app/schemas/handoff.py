"""Handoff inbox schemas (PRD §4.7)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class HandoffOut(BaseModel):
    id: str
    conversation_id: str
    user_id: str
    status: str
    summary: str
    intent: str = "handoff"
    claimed_by: str | None
    claimed_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class StaffReplyRequest(BaseModel):
    content: str
