"""Document upload orchestration."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.document import Document
from app.models.enums import DocumentStatus
from app.services.knowledge.indexer.service import IndexerService
from app.services.knowledge.storage.local import LocalObjectStorage, safe_filename
from app.services.rag.bm25.index import get_default_bm25
from app.services.rag.vector.store import get_default_vector_store
from app.workers.index_worker.queue import IndexJob, get_index_queue


class DocumentService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.storage = LocalObjectStorage()

    async def upload(
        self,
        *,
        filename: str,
        data: bytes,
        title: str | None = None,
        content_type: str = "text/plain",
        uploaded_by: str | None = None,
        index_now: bool = True,
    ) -> Document:
        safe_name = safe_filename(filename)
        doc = Document(
            title=title or safe_name,
            filename=safe_name,
            content_type=content_type,
            status=DocumentStatus.PENDING.value,
            uploaded_by=uploaded_by,
        )
        self.db.add(doc)
        await self.db.flush()

        key = f"documents/{doc.id}/{safe_name}"
        self.storage.put(key, data)
        doc.storage_key = key
        await self.db.flush()

        if index_now:
            await self.schedule_index(doc.id, raw=data)
            await self.db.refresh(doc)
        return doc

    async def schedule_index(self, document_id: str, *, raw: bytes | None = None) -> None:
        """Sync index by default; commit + enqueue when INDEX_ASYNC=1 (non-test)."""
        settings = get_settings()
        if settings.index_async and settings.env != "test":
            # Commit so a concurrent worker session can see the pending document
            await self.db.commit()
            await get_index_queue(settings).enqueue(IndexJob(document_id=document_id))
            return
        await IndexerService(self.db, self.storage).index_document(document_id, raw=raw)

    async def list_documents(self) -> list[Document]:
        result = await self.db.execute(select(Document).order_by(Document.created_at.desc()))
        return list(result.scalars().all())

    async def delete(self, document_id: str) -> bool:
        doc = await self.db.get(Document, document_id)
        if doc is None:
            return False
        if doc.storage_key:
            try:
                self.storage.delete(doc.storage_key)
            except Exception:
                pass
        bm25 = get_default_bm25()
        remaining = [d for d in bm25._docs if str(d.get("doc_id")) != document_id]
        bm25.clear()
        if remaining:
            bm25.add_documents(remaining)
        await get_default_vector_store().delete_document(document_id)
        await self.db.delete(doc)
        await self.db.flush()
        return True
