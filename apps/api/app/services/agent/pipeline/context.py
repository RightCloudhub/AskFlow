"""Pipeline turn context and result DTOs."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.services.agent.cost.ledger import CostLedger
from app.services.agent.harness.policy import Harness
from app.services.agent.intent.classifier import IntentResult
from app.services.agent.slots.state import SlotTracker


@dataclass
class PipelineResult:
    run_id: str
    trace_id: str
    answer: str
    route: str
    intent: str | None
    confidence: float
    flags: list[str] = field(default_factory=list)
    sources: list[dict[str, Any]] = field(default_factory=list)
    metadata_patch: dict[str, Any] = field(default_factory=dict)
    side_effects: dict[str, Any] = field(default_factory=dict)
    cost: dict[str, Any] = field(default_factory=dict)
    verification: dict[str, Any] = field(default_factory=dict)
    rewrite: dict[str, Any] = field(default_factory=dict)
    answer_confidence: float = 0.0
    refused: bool = False


@dataclass
class TurnIds:
    """Run identity + ledger for a single pipeline turn."""

    run_id: str
    trace_id: str
    ledger: CostLedger
    flags: list[str]


@dataclass
class TurnPayload:
    """User text, history, and conversation metadata for a turn."""

    text: str
    history: list[dict[str, Any]]
    metadata: dict[str, Any]
    meta_patch: dict[str, Any] = field(default_factory=dict)


@dataclass
class TurnContext:
    """Immutable-ish bag passed to route handlers."""

    run_id: str
    trace_id: str
    text: str
    history: list[dict[str, Any]]
    metadata: dict[str, Any]
    flags: list[str]
    ledger: CostLedger
    harness: Harness
    slots: SlotTracker
    intent_result: IntentResult | None = None
    side_effects: dict[str, Any] = field(default_factory=dict)
    meta_patch: dict[str, Any] = field(default_factory=dict)
    order_id: str | None = None
    loop: Any = None
    rag: Any = None
