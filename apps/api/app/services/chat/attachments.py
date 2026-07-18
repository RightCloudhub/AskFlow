"""Message attachment metadata (PRD E16) — store refs, not binary in chat path."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

ALLOWED_KINDS = frozenset({"image", "file", "screenshot"})
MAX_ATTACHMENTS = 5
MAX_NAME_LEN = 128
MAX_URL_LEN = 1024


@dataclass
class Attachment:
    kind: str
    name: str = ""
    url: str = ""
    content_type: str = ""
    size_bytes: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "name": self.name[:MAX_NAME_LEN],
            "url": self.url[:MAX_URL_LEN],
            "content_type": self.content_type,
            "size_bytes": self.size_bytes,
        }


def normalize_attachments(raw: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    if not raw:
        return []
    out: list[dict[str, Any]] = []
    for item in raw[:MAX_ATTACHMENTS]:
        kind = str(item.get("kind") or "file").lower()
        if kind not in ALLOWED_KINDS:
            kind = "file"
        att = Attachment(
            kind=kind,
            name=str(item.get("name") or ""),
            url=str(item.get("url") or item.get("ref") or ""),
            content_type=str(item.get("content_type") or ""),
            size_bytes=item.get("size_bytes") if isinstance(item.get("size_bytes"), int) else None,
        )
        out.append(att.to_dict())
    return out


def attachment_prompt_suffix(attachments: list[dict[str, Any]]) -> str:
    if not attachments:
        return ""
    lines = [f"- {a.get('kind')}: {a.get('name') or a.get('url') or 'unnamed'}" for a in attachments]
    return "\n[用户附件]\n" + "\n".join(lines)
