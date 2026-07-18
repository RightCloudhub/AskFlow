"""Optional ChromaDB backend — soft import; no-op when package/host unavailable."""

from __future__ import annotations

import logging
from typing import Any

from app.services.rag.vector.types import VectorHit, VectorRecord

logger = logging.getLogger("askflow.vector.chroma")

DEFAULT_COLLECTION = "askflow"
DEFAULT_CHROMA_PORT = 8001
CHROMA_DISTANCE_COSINE = "cosine"
# Chroma cosine distance → similarity: sim = 1 - distance (when space=cosine)
_SIM_FLOOR = 0.0


class ChromaBackend:
    """Thin wrapper around chromadb PersistentClient or HttpClient."""

    def __init__(
        self,
        *,
        collection: str = DEFAULT_COLLECTION,
        persist_dir: str | None = None,
        host: str | None = None,
        port: int = DEFAULT_CHROMA_PORT,
    ) -> None:
        self.collection_name = collection
        self.persist_dir = persist_dir
        self.host = host
        self.port = port
        self._collection: Any = None
        self._available = False
        self._init()

    @property
    def available(self) -> bool:
        return self._available

    def _init(self) -> None:
        try:
            import chromadb
            from chromadb.config import Settings as ChromaSettings
        except ImportError:
            logger.info("chromadb not installed; vector channel uses memory only")
            return

        try:
            if self.host:
                client = chromadb.HttpClient(host=self.host, port=self.port)
            elif self.persist_dir:
                client = chromadb.PersistentClient(
                    path=self.persist_dir,
                    settings=ChromaSettings(anonymized_telemetry=False),
                )
            else:
                return
            self._collection = client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": CHROMA_DISTANCE_COSINE},
            )
            self._available = True
            logger.info(
                "chroma ready collection=%s host=%s persist=%s",
                self.collection_name,
                self.host,
                self.persist_dir,
            )
        except Exception:
            logger.exception("chroma init failed; falling back to memory")
            self._available = False
            self._collection = None

    def upsert(self, records: list[VectorRecord]) -> int:
        if not self._available or not records:
            return 0
        ids = [r.id for r in records]
        embeddings = [r.embedding for r in records]
        documents = [r.text for r in records]
        metadatas = [
            {
                "doc_id": r.doc_id,
                "source": r.source,
                **{k: _meta_val(v) for k, v in r.meta.items()},
            }
            for r in records
        ]
        self._collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )
        return len(records)

    def delete_by_doc_id(self, doc_id: str) -> None:
        if not self._available:
            return
        try:
            self._collection.delete(where={"doc_id": doc_id})
        except Exception:
            logger.exception("chroma delete failed doc_id=%s", doc_id)

    def search(self, query_vec: list[float], top_k: int = 5) -> list[VectorHit]:
        if not self._available or not query_vec:
            return []
        raw = self._collection.query(
            query_embeddings=[query_vec],
            n_results=max(1, top_k),
            include=["documents", "metadatas", "distances"],
        )
        return _hits_from_query(raw, top_k)


def _meta_val(v: Any) -> str | int | float | bool:
    if isinstance(v, (str, int, float, bool)):
        return v
    return str(v)


def _hits_from_query(raw: dict[str, Any], top_k: int) -> list[VectorHit]:
    docs = (raw.get("documents") or [[]])[0]
    metas = (raw.get("metadatas") or [[]])[0]
    dists = (raw.get("distances") or [[]])[0]
    hits: list[VectorHit] = []
    for i, text in enumerate(docs[:top_k]):
        meta = dict(metas[i] or {}) if i < len(metas) else {}
        dist = float(dists[i]) if i < len(dists) else 1.0
        sim = max(_SIM_FLOOR, 1.0 - dist)
        hits.append(
            VectorHit(
                doc_id=str(meta.get("doc_id", "")),
                source=str(meta.get("source", "unknown")),
                text=str(text or ""),
                score=sim,
                meta={**meta, "channel": "vector", "backend": "chroma", "distance": dist},
            )
        )
    return hits
