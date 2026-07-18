"""Knowledge publish control: generation list / diff / rollback (PRD E10)."""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.models.enums import DocumentStatus
from app.services.knowledge.indexer.service import IndexerService
from app.services.knowledge.revisions import RevisionSnapshot, RevisionStore
from app.services.knowledge.storage.local import LocalObjectStorage


class PublishService:
    def __init__(
        self,
        db: AsyncSession,
        *,
        revisions: RevisionStore | None = None,
        storage: LocalObjectStorage | None = None,
    ) -> None:
        self.db = db
        self.revisions = revisions or RevisionStore()
        self.storage = storage or LocalObjectStorage()

    def list_generations(self, document_id: str) -> list[int]:
        return self.revisions.list_generations(document_id)

    def diff(self, document_id: str, from_gen: int, to_gen: int) -> dict[str, Any]:
        return self.revisions.diff(document_id, from_gen, to_gen)

    async def rollback(self, document_id: str, target_generation: int) -> Document:
        """Restore chunk text from a prior revision and re-index as a new generation."""
        snap = self.revisions.load(document_id, target_generation)
        if snap is None:
            raise ValueError("revision_not_found")
        doc = await self.db.get(Document, document_id)
        if doc is None:
            raise ValueError("document_not_found")
        raw = _raw_from_snapshot(snap)
        # Write body so future reindex has content even if storage_key missing
        key = doc.storage_key or f"documents/{doc.id}/rollback.md"
        self.storage.put(key, raw)
        doc.storage_key = key
        doc.status = DocumentStatus.PENDING.value
        await self.db.flush()
        return await IndexerService(self.db, self.storage).index_document(document_id, raw=raw)


def save_revision_from_chunks(
    document_id: str,
    *,
    generation: int,
    source: str,
    chunks: list[str],
    store: RevisionStore | None = None,
) -> None:
    store = store or RevisionStore()
    store.save(
        RevisionSnapshot(
            document_id=document_id,
            generation=generation,
            source=source,
            chunks=list(chunks),
            chunk_count=len(chunks),
        )
    )


def _raw_from_snapshot(snap: RevisionSnapshot) -> bytes:
    body = "\n\n".join(snap.chunks)
    title = snap.source or "rollback"
    return f"# {title}\n\n{body}\n".encode("utf-8")
