from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.core.deps import CurrentUser, DbSession, require_admin
from app.models.user import User
from app.schemas.knowledge import DocumentOut
from app.services.audit.logger.service import AuditService
from app.services.knowledge.documents import DocumentService

router = APIRouter(dependencies=[Depends(require_admin)])


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
        raise HTTPException(status_code=404, detail="Document not found")
    await AuditService(db).log(
        action="document.delete",
        resource_type="document",
        resource_id=document_id,
        actor_id=user.id,
    )
    return {"ok": True}
