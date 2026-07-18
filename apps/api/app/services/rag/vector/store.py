"""Vector retrieval facade: real embeddings + memory/Chroma backends (PRD §4.2)."""

from __future__ import annotations

import logging
from typing import Any

from app.core.config import Settings, get_settings
from app.services.rag.embedding.client import Embedder
from app.services.rag.embedding.factory import get_embedder
from app.services.rag.vector.chroma_backend import ChromaBackend
from app.services.rag.vector.memory import MemoryVectorIndex
from app.services.rag.vector.types import VectorHit, VectorRecord

logger = logging.getLogger("askflow.vector")

# Re-export for callers that import from store
__all__ = ["VectorHit", "VectorStore", "get_default_vector_store", "reset_default_vector_store"]


class VectorStore:
    """Semantic recall: embed(query) → cosine search (memory always; Chroma optional)."""

    def __init__(
        self,
        *,
        embedder: Embedder | None = None,
        memory: MemoryVectorIndex | None = None,
        chroma: ChromaBackend | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.embedder = embedder or get_embedder(self.settings)
        self.memory = memory if memory is not None else MemoryVectorIndex()
        self.chroma = chroma

    @property
    def backend_name(self) -> str:
        if self.chroma is not None and self.chroma.available:
            return "chroma+memory"
        return "memory"

    async def search(self, query: str, top_k: int = 5) -> list[VectorHit]:
        if not (query or "").strip():
            return []
        vectors = await self.embedder.embed([query])
        if not vectors:
            return []
        qv = vectors[0]
        if self.chroma is not None and self.chroma.available:
            hits = self.chroma.search(qv, top_k=top_k)
            if hits:
                return hits
        return self.memory.search(qv, top_k=top_k)

    async def upsert_chunks(self, chunks: list[dict[str, Any]]) -> int:
        """Embed + upsert chunk dicts (doc_id, source, text, meta fields)."""
        if not chunks:
            return 0
        texts = [str(c.get("text", "")) for c in chunks]
        embeddings = await self.embedder.embed(texts)
        records = _records_from_chunks(chunks, embeddings)
        n = self.memory.upsert(records)
        if self.chroma is not None and self.chroma.available:
            try:
                self.chroma.upsert(records)
            except Exception:
                logger.exception("chroma upsert failed; memory index retained")
        return n

    async def delete_document(self, doc_id: str) -> None:
        self.memory.delete_by_doc_id(doc_id)
        if self.chroma is not None and self.chroma.available:
            self.chroma.delete_by_doc_id(doc_id)


def _records_from_chunks(
    chunks: list[dict[str, Any]],
    embeddings: list[list[float]],
) -> list[VectorRecord]:
    records: list[VectorRecord] = []
    for i, ch in enumerate(chunks):
        doc_id = str(ch.get("doc_id", ""))
        chunk_index = int(ch.get("chunk_index", i))
        generation = ch.get("generation")
        rid = str(ch.get("id") or f"{doc_id}:{generation}:{chunk_index}")
        meta = {
            k: v
            for k, v in ch.items()
            if k not in {"text", "id"}
        }
        records.append(
            VectorRecord(
                id=rid,
                doc_id=doc_id,
                source=str(ch.get("source", "unknown")),
                text=str(ch.get("text", "")),
                embedding=embeddings[i] if i < len(embeddings) else [],
                meta=meta,
            )
        )
    return records


_default_store: VectorStore | None = None


def get_default_vector_store(settings: Settings | None = None) -> VectorStore:
    global _default_store
    if _default_store is None:
        _default_store = _build_default(settings or get_settings())
    return _default_store


def reset_default_vector_store() -> None:
    """Test helper: drop process-global store (re-seeds on next get)."""
    global _default_store
    _default_store = None


def _build_default(settings: Settings) -> VectorStore:
    chroma: ChromaBackend | None = None
    if settings.chroma_persist_dir or settings.chroma_host:
        chroma = ChromaBackend(
            collection=settings.chroma_collection,
            persist_dir=settings.chroma_persist_dir,
            host=settings.chroma_host,
            port=settings.chroma_port,
        )
    store = VectorStore(settings=settings, chroma=chroma)
    # Lazy seed is async — callers that only search after app start use ensure_seeded
    return store


async def ensure_seeded(store: VectorStore | None = None) -> None:
    """Seed memory index with FAQ samples when empty (mirrors BM25 seed)."""
    store = store or get_default_vector_store()
    if len(store.memory) > 0:
        return
    from app.services.rag.bm25.index import seed_documents

    await store.upsert_chunks(seed_documents())
