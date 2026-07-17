"""Chat / conversation schemas (PRD §4.5)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ConversationCreate(BaseModel):
    title: str = Field(default="新会话", max_length=255)


class ConversationUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=255)
    # Users may only close; transfer is system/agent side-effect
    status: str | None = Field(default=None, pattern="^(active|closed)?$")


class ConversationOut(BaseModel):
    id: str
    title: str
    status: str
    metadata: dict[str, Any] = Field(default_factory=dict, validation_alias="metadata_json")
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True, "populate_by_name": True}


class MessageOut(BaseModel):
    id: str
    conversation_id: str
    role: str
    content: str
    meta: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime

    model_config = {"from_attributes": True}


class FeedbackUpsert(BaseModel):
    rating: int = Field(ge=-1, le=1)
    comment: str = ""


class FeedbackOut(BaseModel):
    id: str
    message_id: str
    rating: int
    comment: str

    model_config = {"from_attributes": True}
