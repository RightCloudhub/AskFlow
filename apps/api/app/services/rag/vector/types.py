"""Shared vector hit types."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class VectorHit:
    doc_id: str
    source: str
    text: str
    score: float
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class VectorRecord:
    id: str
    doc_id: str
    source: str
    text: str
    embedding: list[float]
    meta: dict[str, Any] = field(default_factory=dict)
