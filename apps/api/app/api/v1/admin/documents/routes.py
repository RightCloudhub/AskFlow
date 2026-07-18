"""Admin document list / delete / publish control (PRD E10)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.deps import CurrentUser, DbSession, require_admin
from app.models.document import Document
from app.models.user import User
from app.schemas.knowledge import DocumentOut
from app.services.audit.logger.service import AuditService
from app.services.knowledge.documents import DocumentService
from app.services.knowledge.publish import PublishService

router = APIRouter(dependencies=[Depends(require_admin)])

HTTP_NOT_FOUND = 404
HTTP_BAD_REQUEST = 400


@router.get("", response_model=list[DocumentOut])
async def list_documents(db: DbSession, _user: User = Depends(require_admin)) -> list[DocumentOut]:
    rows = await DocumentService(db).list_documents()
    return [DocumentOut.model_validate(r) for r in rows]


@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    db: DbSession,
    user: CurrentUser,
) -> dict:
    ok = await DocumentService(db).delete(document_id)
    if not ok:
        raise HTTPException(status_code=HTTP_NOT_FOUND, detail="Document not found")
    await AuditService(db).log(
        action="document.delete",
        resource_type="document",
        resource_id=document_id,
        actor_id=user.id,
    )
    return {"ok": True}


@router.get("/{document_id}/generations")
async def list_generations(
    document_id: str,
    db: DbSession,
    _user: User = Depends(require_admin),
) -> dict:
    doc = await db.get(Document, document_id)
    if doc is None:
        raise HTTPException(status_code=HTTP_NOT_FOUND, detail="document_not_found")
    gens = PublishService(db).list_generations(document_id)
    return {
        "document_id": document_id,
        "current_generation": doc.generation,
        "generations": gens,
    }


@router.get("/{document_id}/diff")
async def generation_diff(
    document_id: str,
    db: DbSession,
    from_generation: int = Query(..., ge=1),
    to_generation: int = Query(..., ge=1),
    _user: User = Depends(require_admin),
) -> dict:
    try:
        return PublishService(db).diff(document_id, from_generation, to_generation)
    except ValueError as exc:
        raise HTTPException(status_code=HTTP_NOT_FOUND, detail=str(exc)) from exc


@router.post("/{document_id}/rollback", response_model=DocumentOut)
async def rollback_generation(
    document_id: str,
    db: DbSession,
    user: CurrentUser,
    target_generation: int = Query(..., ge=1),
) -> DocumentOut:
    try:
        doc = await PublishService(db).rollback(document_id, target_generation)
    except ValueError as exc:
        code = HTTP_NOT_FOUND if "not_found" in str(exc) else HTTP_BAD_REQUEST
        raise HTTPException(status_code=code, detail=str(exc)) from exc
    await AuditService(db).log(
        action="document.rollback",
        resource_type="document",
        resource_id=document_id,
        actor_id=user.id,
        detail={"target_generation": target_generation, "new_generation": doc.generation},
    )
    return DocumentOut.model_validate(doc)
