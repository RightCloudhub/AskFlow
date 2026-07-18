"""TICKET route — emit create side-effect only."""

from __future__ import annotations

from app.models.enums import Route
from app.services.agent.pipeline.context import PipelineResult, TurnContext

TITLE_MAX = 80
TITLE_BODY_MAX = 64


def _ticket_title(intent: str, text: str) -> str:
    """Stable, type-prefixed title — reduces false open-ticket merges on raw text."""
    body = (text or "").strip()[:TITLE_BODY_MAX] or "用户请求"
    title = f"[{intent}] {body}"
    return title[:TITLE_MAX]


async def handle_ticket(ctx: TurnContext) -> PipelineResult:
    intent = ctx.intent_result.intent.value if ctx.intent_result else "fault_report"
    confidence = ctx.intent_result.confidence if ctx.intent_result else 0.8
    title = _ticket_title(intent, ctx.text)
    se = {
        **ctx.side_effects,
        "ticket": {
            "action": "create",
            "title": title,
            "type": intent,
            "priority": "high",
            "description": ctx.text,
        },
    }
    final = ctx.harness.finalize(
        f"已为您登记工单「{title}」。我们会尽快处理，您可在「我的工单」中查看进度。"
    )
    return PipelineResult(
        run_id=ctx.run_id,
        trace_id=ctx.trace_id,
        answer=final.text,
        route=Route.TICKET.value,
        intent=intent,
        confidence=confidence,
        flags=list(ctx.flags) + final.flags,
        side_effects=se,
        cost=ctx.ledger.summary(),
    )
