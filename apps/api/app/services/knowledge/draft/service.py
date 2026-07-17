"""Knowledge draft review → publish into index (PRD §4.9)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.models.enums import DocumentStatus, DraftStatus
from app.models.knowledge import KnowledgeDraft
from app.services.knowledge.gap.service import GapService
from app.services.knowledge.indexer.service import IndexerService
from app.services.knowledge.storage.local import LocalObjectStorage


class DraftService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.storage = LocalObjectStorage()

    async def create(
        self,
        *,
        title: str,
        content: str,
        created_by: str | None = None,
        gap_id: str | None = None,
    ) -> KnowledgeDraft:
        draft = KnowledgeDraft(
            title=title,
            content=content,
            created_by=created_by,
            gap_id=gap_id,
            status=DraftStatus.DRAFT.value,
        )
        self.db.add(draft)
        await self.db.flush()
        await self.db.refresh(draft)
        return draft

    async def list_drafts(self, status: str | None = None) -> list[KnowledgeDraft]:
        stmt = select(KnowledgeDraft).order_by(KnowledgeDraft.created_at.desc())
        if status:
            stmt = stmt.where(KnowledgeDraft.status == status)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def approve(self, draft_id: str, reviewer_id: str) -> KnowledgeDraft:
        draft = await self.db.get(KnowledgeDraft, draft_id)
        if draft is None:
            raise ValueError("draft_not_found")
        if draft.status != DraftStatus.DRAFT.value:
            raise ValueError("draft_not_pending")

        # publish as document + index
        filename = f"{draft.id}.md"
        raw = f"# {draft.title}\n\n{draft.content}".encode("utf-8")
        storage_key = f"drafts/{draft.id}/{filename}"
        self.storage.put(storage_key, raw)

        doc = Document(
            title=draft.title,
            filename=filename,
            content_type="text/markdown",
            status=DocumentStatus.PENDING.value,
            storage_key=storage_key,
            uploaded_by=reviewer_id,
        )
        self.db.add(doc)
        await self.db.flush()

        indexer = IndexerService(self.db, self.storage)
        await indexer.index_document(doc.id, raw=raw)

        draft.status = DraftStatus.APPROVED.value
        draft.reviewed_by = reviewer_id
        draft.document_id = doc.id
        if draft.gap_id:
            await GapService(self.db).mark_promoted(draft.gap_id)
        await self.db.flush()
        await self.db.refresh(draft)
        return draft

    async def reject(self, draft_id: str, reviewer_id: str) -> KnowledgeDraft:
        draft = await self.db.get(KnowledgeDraft, draft_id)
        if draft is None:
            raise ValueError("draft_not_found")
        draft.status = DraftStatus.REJECTED.value
        draft.reviewed_by = reviewer_id
        await self.db.flush()
        await self.db.refresh(draft)
        return draft
