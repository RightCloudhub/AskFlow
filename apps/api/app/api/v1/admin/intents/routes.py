from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from app.core.deps import CurrentUser, DbSession, require_admin
from app.models.enums import LEGAL_INTENTS, LEGAL_ROUTES
from app.models.intent_config import IntentConfig
from app.models.user import User
from app.schemas.knowledge import IntentConfigIn, IntentConfigOut
from app.services.agent.router.decision import RouteResolver
from app.services.audit.logger.service import AuditService

router = APIRouter(dependencies=[Depends(require_admin)])


@router.get("", response_model=list[IntentConfigOut])
async def list_intents(db: DbSession, _user: User = Depends(require_admin)) -> list[IntentConfigOut]:
    result = await db.execute(select(IntentConfig).order_by(IntentConfig.intent))
    return [IntentConfigOut.model_validate(r) for r in result.scalars().all()]


@router.put("/{intent}", response_model=IntentConfigOut)
async def upsert_intent(
    intent: str,
    payload: IntentConfigIn,
    db: DbSession,
    user: CurrentUser,
) -> IntentConfigOut:
    if intent not in {i.value for i in LEGAL_INTENTS}:
        raise HTTPException(status_code=400, detail="Illegal intent (cold set)")
    if payload.route not in {r.value for r in LEGAL_ROUTES}:
        raise HTTPException(status_code=400, detail="Illegal route (cold set)")

    result = await db.execute(select(IntentConfig).where(IntentConfig.intent == intent))
    row = result.scalar_one_or_none()
    if row is None:
        row = IntentConfig(
            intent=intent,
            route=payload.route,
            enabled=payload.enabled,
            description=payload.description,
            min_confidence=payload.min_confidence,
        )
        db.add(row)
    else:
        row.route = payload.route
        row.enabled = payload.enabled
        row.description = payload.description
        row.min_confidence = payload.min_confidence
    await db.flush()
    await db.refresh(row)
    RouteResolver(db).invalidate()
    await AuditService(db).log(
        action="intent.upsert",
        resource_type="intent_config",
        resource_id=row.id,
        actor_id=user.id,
        detail={"intent": intent, "route": payload.route},
    )
    return IntentConfigOut.model_validate(row)
