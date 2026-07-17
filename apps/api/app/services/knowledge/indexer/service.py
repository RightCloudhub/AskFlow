"""Document indexer: parse → chunk → BM25 (write-new-then-delete generation) (PRD §4.8)."""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.models.enums import DocumentStatus
from app.services.knowledge.chunker.chunker import chunk_text
from app.services.knowledge.parser.parser import parse_bytes
from app.services.knowledge.storage.local import LocalObjectStorage
from app.services.rag.bm25.index import get_default_bm25


class IndexerService:
    def __init__(self, db: AsyncSession, storage: LocalObjectStorage | None = None) -> None:
        self.db = db
        self.storage = storage or LocalObjectStorage()

    async def index_document(self, document_id: str, raw: bytes | None = None) -> Document:
        from sqlalchemy import update

        doc = await self.db.get(Document, document_id)
        if doc is None:
            raise ValueError("document_not_found")

        # CAS: only one concurrent indexer moves pending/active/failed → indexing
        cas = await self.db.execute(
            update(Document)
            .where(
                Document.id == document_id,
                Document.status.in_(
                    [
                        DocumentStatus.PENDING.value,
                        DocumentStatus.ACTIVE.value,
                        DocumentStatus.FAILED.value,
                    ]
                ),
            )
            .values(status=DocumentStatus.INDEXING.value)
        )
        if cas.rowcount == 0:
            # another worker is indexing — return current row
            await self.db.refresh(doc)
            if doc.status == DocumentStatus.ACTIVE.value:
                return doc
            raise ValueError("indexing_in_progress")

        await self.db.refresh(doc)

        try:
            if raw is None:
                if not doc.storage_key:
                    raise ValueError("no_storage_key")
                raw = self.storage.get(doc.storage_key)

            text = parse_bytes(raw, filename=doc.filename, content_type=doc.content_type)
            chunks = chunk_text(text)
            generation = (doc.generation or 0) + 1

            # write-new-then-delete: add new generation chunks, then drop old for this doc_id
            bm25 = get_default_bm25()
            remaining = [
                d
                for d in bm25._docs
                if str(d.get("doc_id")) != doc.id
            ]
            bm25.clear()
            if remaining:
                bm25.add_documents(remaining)

            new_docs: list[dict[str, Any]] = []
            for i, ch in enumerate(chunks):
                new_docs.append(
                    {
                        "doc_id": doc.id,
                        "source": doc.title or doc.filename,
                        "text": ch,
                        "generation": generation,
                        "chunk_index": i,
                        "indexed_at": None,
                    }
                )
            if new_docs:
                bm25.add_documents(new_docs)

            doc.generation = generation
            doc.chunk_count = len(chunks)
            doc.status = DocumentStatus.ACTIVE.value
            doc.error_message = None
            await self.db.flush()
            await self.db.refresh(doc)
            return doc
        except Exception as exc:
            doc.status = DocumentStatus.FAILED.value
            doc.error_message = str(exc)[:500]
            await self.db.flush()
            await self.db.refresh(doc)
            raise
