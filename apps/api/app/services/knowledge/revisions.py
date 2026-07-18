"""Document generation revisions for publish diff / rollback (PRD E10)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.core.config import get_settings

REVISIONS_SUBDIR = "revisions"
MANIFEST_NAME = "manifest.json"


@dataclass
class RevisionSnapshot:
    document_id: str
    generation: int
    source: str
    chunks: list[str]
    chunk_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "document_id": self.document_id,
            "generation": self.generation,
            "source": self.source,
            "chunks": self.chunks,
            "chunk_count": self.chunk_count,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RevisionSnapshot:
        return cls(
            document_id=str(data["document_id"]),
            generation=int(data["generation"]),
            source=str(data.get("source") or ""),
            chunks=[str(c) for c in data.get("chunks") or []],
            chunk_count=int(data.get("chunk_count") or len(data.get("chunks") or [])),
        )


class RevisionStore:
    """Filesystem-backed generation snapshots (write-new-then-delete companion)."""

    def __init__(self, root: Path | None = None) -> None:
        base = root or Path(get_settings().revision_store_dir)
        self.root = base
        self.root.mkdir(parents=True, exist_ok=True)

    def _doc_dir(self, document_id: str) -> Path:
        path = self.root / REVISIONS_SUBDIR / document_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def save(self, snap: RevisionSnapshot) -> Path:
        d = self._doc_dir(snap.document_id)
        path = d / f"g{snap.generation}.json"
        path.write_text(json.dumps(snap.to_dict(), ensure_ascii=False), encoding="utf-8")
        self._update_manifest(snap.document_id, snap.generation)
        return path

    def list_generations(self, document_id: str) -> list[int]:
        d = self._doc_dir(document_id)
        gens: list[int] = []
        for p in d.glob("g*.json"):
            try:
                gens.append(int(p.stem[1:]))
            except ValueError:
                continue
        return sorted(gens)

    def load(self, document_id: str, generation: int) -> RevisionSnapshot | None:
        path = self._doc_dir(document_id) / f"g{generation}.json"
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        return RevisionSnapshot.from_dict(data)

    def diff(
        self,
        document_id: str,
        from_generation: int,
        to_generation: int,
    ) -> dict[str, Any]:
        left = self.load(document_id, from_generation)
        right = self.load(document_id, to_generation)
        if left is None or right is None:
            raise ValueError("revision_not_found")
        left_set = set(left.chunks)
        right_set = set(right.chunks)
        return {
            "document_id": document_id,
            "from_generation": from_generation,
            "to_generation": to_generation,
            "added": sorted(right_set - left_set),
            "removed": sorted(left_set - right_set),
            "unchanged_count": len(left_set & right_set),
            "from_chunk_count": left.chunk_count,
            "to_chunk_count": right.chunk_count,
        }

    def _update_manifest(self, document_id: str, generation: int) -> None:
        d = self._doc_dir(document_id)
        path = d / MANIFEST_NAME
        gens = self.list_generations(document_id)
        if generation not in gens:
            gens.append(generation)
            gens.sort()
        path.write_text(
            json.dumps({"document_id": document_id, "generations": gens}, ensure_ascii=False),
            encoding="utf-8",
        )
