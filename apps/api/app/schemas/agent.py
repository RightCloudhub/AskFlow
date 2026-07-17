"""Agent classify / pipeline debug schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ClassifyRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000)
    history: list[dict[str, str]] = Field(default_factory=list)


class ClassifyResponse(BaseModel):
    intent: str
    confidence: float
    source: str  # rule | llm | fallback
    route: str
    flags: list[str] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)


class RAGQueryRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=20)
    filters: dict[str, Any] = Field(default_factory=dict)


class RAGSource(BaseModel):
    index: int
    doc_id: str | None = None
    source: str
    text: str
    score: float


class RAGQueryResponse(BaseModel):
    answer: str
    refused: bool = False
    refusal_reason: str | None = None
    confidence: float = 0.0
    sources: list[RAGSource] = Field(default_factory=list)
    rewrite: dict[str, Any] = Field(default_factory=dict)
    verification: dict[str, Any] = Field(default_factory=dict)
