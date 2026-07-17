"""Shared API envelope and pagination."""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class APIEnvelope(BaseModel, Generic[T]):
    ok: bool = True
    data: T | None = None
    error: str | None = None
    code: str | None = None


class PageMeta(BaseModel):
    page: int = 1
    page_size: int = 20
    total: int = 0


class Page(BaseModel, Generic[T]):
    items: list[T]
    meta: PageMeta


class HealthDependency(BaseModel):
    name: str
    status: str  # up | down | degraded
    detail: str | None = None


class HealthResponse(BaseModel):
    status: str
    version: str
    env: str
    dependencies: list[HealthDependency] = Field(default_factory=list)
    extras: dict[str, Any] = Field(default_factory=dict)
