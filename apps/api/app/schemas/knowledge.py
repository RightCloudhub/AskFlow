"""Knowledge / document / gap / draft DTOs."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class DocumentOut(BaseModel):
    id: str
    title: str
    filename: str
    content_type: str
    status: str
    generation: int
    chunk_count: int
    error_message: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class GapOut(BaseModel):
    id: str
    question: str
    normalized_question: str
    status: str
    hit_count: int
    intent: str | None
    reason: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class DraftCreate(BaseModel):
    title: str = Field(min_length=1, max_length=512)
    content: str = Field(min_length=1)
    gap_id: str | None = None


class DraftOut(BaseModel):
    id: str
    title: str
    content: str
    status: str
    gap_id: str | None
    document_id: str | None
    created_by: str | None
    reviewed_by: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class IntentConfigIn(BaseModel):
    intent: str
    route: str
    enabled: bool = True
    description: str = ""
    min_confidence: float = 0.0


class IntentConfigOut(BaseModel):
    id: str
    intent: str
    route: str
    enabled: bool
    description: str
    min_confidence: float

    model_config = {"from_attributes": True}


class PromptTemplateOut(BaseModel):
    id: str
    key: str
    description: str
    active_version_id: str | None

    model_config = {"from_attributes": True}


class PromptVersionIn(BaseModel):
    content: str
    activate: bool = True


class PromptVersionOut(BaseModel):
    id: str
    template_id: str
    version: int
    content: str

    model_config = {"from_attributes": True}


class AuditLogOut(BaseModel):
    id: str
    actor_id: str | None
    action: str
    resource_type: str
    resource_id: str | None
    detail: dict
    created_at: datetime

    model_config = {"from_attributes": True}
