"""Agent classify debug endpoint (PRD §7.1)."""

from __future__ import annotations

from fastapi import APIRouter

from app.core.deps import CurrentUser, DbSession
from app.middleware.metrics import INTENT_TOTAL, ROUTE_TOTAL
from app.schemas.agent import ClassifyRequest, ClassifyResponse
from app.services.agent.harness.policy import Harness
from app.services.agent.intent.classifier import IntentClassifier
from app.services.agent.router.decision import RouteResolver

router = APIRouter()


@router.post("/classify", response_model=ClassifyResponse)
async def classify(
    payload: ClassifyRequest,
    user: CurrentUser,
    db: DbSession,
) -> ClassifyResponse:
    _ = user
    harness = Harness()
    prep = harness.prepare(payload.text, payload.history)
    if not prep.allowed:
        return ClassifyResponse(
            intent="faq",
            confidence=0.0,
            source="harness",
            route="blocked",
            flags=prep.flags,
            reasons=[prep.reason or "blocked"],
        )

    intent = await IntentClassifier().classify(prep.text, prep.history)
    resolved = await RouteResolver(db).resolve(intent.intent)
    decision = harness.choose_route(
        resolved.route,
        confidence=intent.confidence,
        needs_clarify=intent.needs_clarify,
    )
    INTENT_TOTAL.labels(intent=intent.intent.value, source=intent.source).inc()
    ROUTE_TOTAL.labels(route=decision.route.value, forced=str(decision.forced).lower()).inc()
    return ClassifyResponse(
        intent=intent.intent.value,
        confidence=intent.confidence,
        source=intent.source,
        route=decision.route.value,
        flags=list(prep.flags) + list(decision.flags),
        reasons=intent.reasons or [],
    )
