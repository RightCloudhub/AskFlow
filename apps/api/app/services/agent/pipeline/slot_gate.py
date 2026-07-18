"""Slot short-circuit gate before (or with) intent classify.

Preserves raw metadata patches (including ``None`` deletes) so ChatService
can merge onto real conversation metadata — never pre-apply deletes on {}.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

from app.services.agent.intent.classifier import IntentResult
from app.services.agent.slots.state import SlotDecision, SlotTracker

ClassifyFn = Callable[[str, list[dict[str, Any]] | None], Awaitable[IntentResult]]


@dataclass
class SlotGateOutcome:
    """Outcome of the pre-dispatch slot gate."""

    kind: str  # none | ask | filled | abandon | continue
    decision: SlotDecision | None = None
    meta_patch: dict[str, Any] = field(default_factory=dict)
    intent_result: IntentResult | None = None


def raw_patch(decision: SlotDecision) -> dict[str, Any]:
    """Copy decision.patch as-is (keep None deletes)."""
    if not decision.patch:
        return {}
    return dict(decision.patch)


async def evaluate_slot_gate(
    tracker: SlotTracker,
    text: str,
    meta: dict[str, Any],
    *,
    history: list[dict[str, Any]] | None,
    classify: ClassifyFn,
) -> SlotGateOutcome:
    """Decide whether to short-circuit on tool slots or continue to classify."""
    order_id = tracker.extract_order_id(text)
    has_pending = isinstance(meta.get("pending_slot"), dict)

    if has_pending and not order_id:
        return await _pending_without_order(
            tracker, text, meta, history=history, classify=classify
        )

    if order_id:
        decision = tracker.decide(text, meta)
        if decision.action == "filled" and decision.order_id:
            patch = raw_patch(decision) or {"pending_slot": None}
            return SlotGateOutcome(kind="filled", decision=decision, meta_patch=patch)

    return SlotGateOutcome(kind="none")


async def _pending_without_order(
    tracker: SlotTracker,
    text: str,
    meta: dict[str, Any],
    *,
    history: list[dict[str, Any]] | None,
    classify: ClassifyFn,
) -> SlotGateOutcome:
    intent_result = await classify(text, history)
    decision = tracker.decide(
        text,
        meta,
        new_intent=intent_result.intent.value,
        new_intent_confidence=intent_result.confidence,
    )
    patch = raw_patch(decision)

    if decision.action == "ask":
        return SlotGateOutcome(kind="ask", decision=decision, meta_patch=patch)

    if decision.action == "abandon":
        if decision.message:
            return SlotGateOutcome(
                kind="abandon",
                decision=decision,
                meta_patch=patch or {"pending_slot": None},
            )
        # High-confidence intent switch: clear slot and reuse classification
        return SlotGateOutcome(
            kind="continue",
            decision=decision,
            meta_patch=patch or {"pending_slot": None},
            intent_result=intent_result,
        )

    return SlotGateOutcome(kind="none", intent_result=intent_result)


def attach_meta_patch(
    result: Any,
    meta_patch: dict[str, Any] | None,
) -> Any:
    """Merge raw patch onto PipelineResult.metadata_patch (preserves None)."""
    if not meta_patch:
        return result
    current = dict(getattr(result, "metadata_patch", None) or {})
    current.update(meta_patch)
    result.metadata_patch = current
    return result
