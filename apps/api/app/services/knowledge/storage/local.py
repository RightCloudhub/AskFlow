"""Local filesystem object storage adapter (MinIO/S3-compatible later)."""

from __future__ import annotations

from pathlib import Path

from app.core.config import get_settings


class LocalObjectStorage:
    def __init__(self, root: str | Path | None = None) -> None:
        settings = get_settings()
        base = root or Path(settings.database_url.split("///")[-1]).parent / "uploads" if "sqlite" in settings.database_url else Path("./uploads")
        if root:
            base = Path(root)
        else:
            base = Path("./data/uploads")
        self.root = base
        self.root.mkdir(parents=True, exist_ok=True)

    def put(self, key: str, data: bytes) -> str:
        path = self.root / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return str(path)

    def get(self, key: str) -> bytes:
        return (self.root / key).read_bytes()

    def delete(self, key: str) -> None:
        path = self.root / key
        if path.exists():
            path.unlink()
