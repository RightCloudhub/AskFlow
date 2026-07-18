"""Small PipelineResult builders for early-exit turn paths."""

from __future__ import annotations

from typing import Any

from app.models.enums import Intent, Route
from app.services.agent.harness.policy import Harness
from app.services.agent.pipeline.context import PipelineResult, TurnIds


def transferred_result(ids: TurnIds, harness: Harness) -> PipelineResult:
    return PipelineResult(
        run_id=ids.run_id,
        trace_id=ids.trace_id,
        answer=harness.transferred_message(),
        route="noop",
        intent=None,
        confidence=1.0,
        flags=ids.flags + ["transferred_skip_ai"],
        cost=ids.ledger.summary(),
    )


def blocked_result(ids: TurnIds, answer: str) -> PipelineResult:
    return PipelineResult(
        run_id=ids.run_id,
        trace_id=ids.trace_id,
        answer=answer,
        route="blocked",
        intent=None,
        confidence=1.0,
        flags=ids.flags,
        cost=ids.ledger.summary(),
    )


def slot_ask_result(
    ids: TurnIds,
    harness: Harness,
    message: str | None,
    meta_patch: dict[str, Any],
) -> PipelineResult:
    final = harness.finalize(message)
    return PipelineResult(
        run_id=ids.run_id,
        trace_id=ids.trace_id,
        answer=final.text,
        route=Route.TOOL.value,
        intent=Intent.ORDER_QUERY.value,
        confidence=0.9,
        flags=ids.flags + final.flags + ["slot_ask"],
        metadata_patch=meta_patch,
        cost=ids.ledger.summary(),
    )


def slot_abandon_result(
    ids: TurnIds,
    harness: Harness,
    message: str | None,
    meta_patch: dict[str, Any],
) -> PipelineResult:
    final = harness.finalize(message or "")
    return PipelineResult(
        run_id=ids.run_id,
        trace_id=ids.trace_id,
        answer=final.text,
        route=Route.TOOL.value,
        intent=Intent.ORDER_QUERY.value,
        confidence=0.5,
        flags=ids.flags + final.flags + ["slot_abandon"],
        metadata_patch=meta_patch or {"pending_slot": None},
        cost=ids.ledger.summary(),
    )
