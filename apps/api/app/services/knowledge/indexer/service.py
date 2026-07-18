"""Document indexer: parse → chunk → BM25 + embed → vector upsert (PRD §4.8)."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.models.enums import DocumentStatus
from app.services.knowledge.chunker.chunker import chunk_text
from app.services.knowledge.parser.parser import parse_bytes
from app.services.knowledge.storage.local import LocalObjectStorage
from app.services.rag.bm25.index import get_default_bm25
from app.services.rag.vector.store import get_default_vector_store

logger = logging.getLogger("askflow.indexer")

ERROR_MSG_MAX = 500


class IndexerService:
    def __init__(self, db: AsyncSession, storage: LocalObjectStorage | None = None) -> None:
        self.db = db
        self.storage = storage or LocalObjectStorage()

    async def index_document(self, document_id: str, raw: bytes | None = None) -> Document:
        doc = await self.db.get(Document, document_id)
        if doc is None:
            raise ValueError("document_not_found")

        if not await self._claim_indexing(document_id):
            await self.db.refresh(doc)
            if doc.status == DocumentStatus.ACTIVE.value:
                return doc
            raise ValueError("indexing_in_progress")

        await self.db.refresh(doc)
        try:
            text = await self._load_text(doc, raw)
            chunks = chunk_text(text)
            generation = (doc.generation or 0) + 1
            new_docs = _chunk_payloads(doc, chunks, generation)
            _replace_bm25(doc.id, new_docs)
            await get_default_vector_store().delete_document(doc.id)
            if new_docs:
                await get_default_vector_store().upsert_chunks(new_docs)
            from app.services.knowledge.publish import save_revision_from_chunks

            save_revision_from_chunks(
                doc.id,
                generation=generation,
                source=str(doc.title or doc.filename),
                chunks=chunks,
            )
            doc.generation = generation
            doc.chunk_count = len(chunks)
            doc.status = DocumentStatus.ACTIVE.value
            doc.error_message = None
            await self.db.flush()
            await self.db.refresh(doc)
            return doc
        except Exception as exc:
            doc.status = DocumentStatus.FAILED.value
            doc.error_message = str(exc)[:ERROR_MSG_MAX]
            await self.db.flush()
            await self.db.refresh(doc)
            raise

    async def _claim_indexing(self, document_id: str) -> bool:
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
        return cas.rowcount > 0

    async def _load_text(self, doc: Document, raw: bytes | None) -> str:
        if raw is None:
            if not doc.storage_key:
                raise ValueError("no_storage_key")
            raw = self.storage.get(doc.storage_key)
        return parse_bytes(raw, filename=doc.filename, content_type=doc.content_type)


def _chunk_payloads(doc: Document, chunks: list[str], generation: int) -> list[dict[str, Any]]:
    return [
        {
            "doc_id": doc.id,
            "source": doc.title or doc.filename,
            "text": ch,
            "generation": generation,
            "chunk_index": i,
            "indexed_at": None,
        }
        for i, ch in enumerate(chunks)
    ]


def _replace_bm25(doc_id: str, new_docs: list[dict[str, Any]]) -> None:
    """write-new-then-delete for this doc_id in the process BM25 index."""
    bm25 = get_default_bm25()
    remaining = [d for d in bm25._docs if str(d.get("doc_id")) != doc_id]
    bm25.clear()
    if remaining:
        bm25.add_documents(remaining)
    if new_docs:
        bm25.add_documents(new_docs)
