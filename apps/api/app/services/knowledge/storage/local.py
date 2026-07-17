"""Local filesystem object storage adapter (MinIO/S3-compatible later)."""

from __future__ import annotations

from pathlib import Path

from app.core.config import get_settings


def safe_filename(filename: str | None, *, fallback: str = "upload.bin") -> str:
    """Basename only — blocks path traversal and separators."""
    name = Path(filename or fallback).name
    if not name or name in {".", ".."}:
        name = fallback
    cleaned = "".join(c if c.isalnum() or c in "._-" else "_" for c in name)
    cleaned = cleaned.strip("._") or fallback
    return cleaned[:128]


class LocalObjectStorage:
    def __init__(self, root: str | Path | None = None) -> None:
        settings = get_settings()
        if root:
            base = Path(root)
        else:
            _ = settings  # keep settings available for future s3 switch
            base = Path("./data/uploads")
        self.root = base
        self.root.mkdir(parents=True, exist_ok=True)

    def _resolved_path(self, key: str) -> Path:
        # Reject absolute / parent traversal in key segments
        parts = [p for p in Path(key).parts if p not in ("", ".")]
        if any(p == ".." for p in parts):
            raise ValueError("path_escape")
        path = (self.root.joinpath(*parts)).resolve()
        root = self.root.resolve()
        try:
            path.relative_to(root)
        except ValueError as exc:
            raise ValueError("path_escape") from exc
        return path

    def put(self, key: str, data: bytes) -> str:
        path = self._resolved_path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return str(path)

    def get(self, key: str) -> bytes:
        return self._resolved_path(key).read_bytes()

    def delete(self, key: str) -> None:
        path = self._resolved_path(key)
        if path.exists():
            path.unlink()
