"""Ticket schemas (PRD §4.6)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class TicketCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str = ""
    type: str = "user_created"
    priority: str = "medium"
    conversation_id: str | None = None
    content: dict[str, Any] = Field(default_factory=dict)


class TicketUpdate(BaseModel):
    status: str | None = None
    priority: str | None = None
    assignee: str | None = None
    description: str | None = None


class TicketOut(BaseModel):
    id: str
    user_id: str
    conversation_id: str | None
    type: str
    status: str
    priority: str
    title: str
    description: str
    assignee: str | None
    content: dict[str, Any]
    resolved_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
