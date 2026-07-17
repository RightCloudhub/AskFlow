from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.core.deps import CurrentUser, DbSession, require_admin
from app.models.user import User
from app.schemas.knowledge import PromptTemplateOut, PromptVersionIn, PromptVersionOut
from app.services.audit.logger.service import AuditService
from app.services.prompt.service import PromptService

router = APIRouter(dependencies=[Depends(require_admin)])


@router.get("", response_model=list[PromptTemplateOut])
async def list_prompts(db: DbSession, _user: User = Depends(require_admin)) -> list[PromptTemplateOut]:
    svc = PromptService(db)
    await svc.ensure_defaults()
    rows = await svc.list_templates()
    return [PromptTemplateOut.model_validate(r) for r in rows]


@router.post("/{key}/versions", response_model=PromptVersionOut)
async def add_version(
    key: str,
    payload: PromptVersionIn,
    db: DbSession,
    user: CurrentUser,
) -> PromptVersionOut:
    svc = PromptService(db)
    ver = await svc.add_version(
        key, payload.content, created_by=user.id, activate=payload.activate
    )
    await AuditService(db).log(
        action="prompt.version",
        resource_type="prompt",
        resource_id=key,
        actor_id=user.id,
        detail={"version": ver.version, "activate": payload.activate},
    )
    return PromptVersionOut.model_validate(ver)


@router.post("/{key}/activate/{version}", response_model=PromptTemplateOut)
async def activate_version(
    key: str,
    version: int,
    db: DbSession,
    user: CurrentUser,
) -> PromptTemplateOut:
    try:
        tpl = await PromptService(db).activate_version(key, version)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    await AuditService(db).log(
        action="prompt.activate",
        resource_type="prompt",
        resource_id=key,
        actor_id=user.id,
        detail={"version": version},
    )
    return PromptTemplateOut.model_validate(tpl)


@router.get("/{key}/active")
async def get_active(key: str, db: DbSession, _user: User = Depends(require_admin)) -> dict:
    content = await PromptService(db).get_active_content(key)
    if content is None:
        raise HTTPException(status_code=404, detail="No active content")
    return {"key": key, "content": content}
