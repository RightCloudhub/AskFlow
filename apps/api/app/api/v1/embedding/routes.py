"""Document upload / reindex (PRD §4.8 / §7.1)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app.core.config import get_settings
from app.core.deps import CurrentUser, DbSession, require_admin
from app.models.document import Document
from app.models.user import User
from app.schemas.knowledge import DocumentOut
from app.services.audit.logger.service import AuditService
from app.services.knowledge.documents import DocumentService
from app.services.knowledge.indexer.service import IndexerService
from app.workers.index_worker.queue import IndexJob, get_index_queue

router = APIRouter()

HTTP_BAD_REQUEST = 400
HTTP_PAYLOAD_TOO_LARGE = 413
HTTP_NOT_FOUND = 404


class DocumentMetadataForm:
    """Grouped optional upload metadata; keeps the route signature small (arch §4.7)."""

    def __init__(
        self,
        *,
        title: str | None = Form(default=None),
        language: str | None = Form(default=None),
        product: str | None = Form(default=None),
        acl_groups: str | None = Form(default=None),
        valid_from: str | None = Form(default=None),
        valid_to: str | None = Form(default=None),
    ) -> None:
        self.title = title
        self.language = language
        self.product = product
        self.acl_groups = [g.strip() for g in (acl_groups or "").split(",") if g.strip()]
        self.valid_from = _parse_validity(valid_from)
        self.valid_to = _parse_validity(valid_to)


@router.post("/upload", response_model=DocumentOut)
async def upload_document(
    db: DbSession,
    user: CurrentUser,
    file: UploadFile = File(...),
    meta: DocumentMetadataForm = Depends(),
    _admin: User = Depends(require_admin),
) -> DocumentOut:
    max_bytes = get_settings().max_upload_bytes
    data = await file.read(max_bytes + 1)
    if not data:
        raise HTTPException(status_code=HTTP_BAD_REQUEST, detail="Empty file")
    if len(data) > max_bytes:
        raise HTTPException(status_code=HTTP_PAYLOAD_TOO_LARGE, detail="file_too_large")
    doc = await DocumentService(db).upload(
        filename=file.filename or "upload.txt",
        data=data,
        title=meta.title,
        content_type=file.content_type or "text/plain",
        uploaded_by=user.id,
        index_now=True,
        language=meta.language,
        product=meta.product,
        acl_groups=meta.acl_groups,
        valid_from=meta.valid_from,
        valid_to=meta.valid_to,
    )
    await AuditService(db).log(
        action="document.upload",
        resource_type="document",
        resource_id=doc.id,
        actor_id=user.id,
        detail={"filename": file.filename, "title": meta.title or file.filename},
    )
    return DocumentOut.model_validate(doc)


@router.post("/reindex/{document_id}", response_model=DocumentOut)
async def reindex_document(
    document_id: str,
    db: DbSession,
    user: CurrentUser,
    _admin: User = Depends(require_admin),
) -> DocumentOut:
    settings = get_settings()
    try:
        doc = await _reindex(db, document_id, settings)
    except ValueError as exc:
        raise HTTPException(status_code=HTTP_NOT_FOUND, detail=str(exc)) from exc
    await AuditService(db).log(
        action="document.reindex",
        resource_type="document",
        resource_id=doc.id,
        actor_id=user.id,
    )
    return DocumentOut.model_validate(doc)


async def _reindex(db, document_id: str, settings) -> Document:
    if settings.index_async and settings.env != "test":
        doc = await db.get(Document, document_id)
        if doc is None:
            raise ValueError("document_not_found")
        await db.commit()
        await get_index_queue(settings).enqueue(IndexJob(document_id=document_id))
        await db.refresh(doc)
        return doc
    return await IndexerService(db).index_document(document_id)


def _parse_validity(value: str | None):
    if not value:
        return None
    from datetime import datetime

    try:
        return datetime.fromisoformat(value)
    except ValueError:
        raise HTTPException(status_code=HTTP_BAD_REQUEST, detail="invalid_validity") from None
