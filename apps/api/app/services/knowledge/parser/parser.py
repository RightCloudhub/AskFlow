"""Document parsers for txt / markdown / plain bytes (PRD §4.8)."""

from __future__ import annotations


def parse_bytes(data: bytes, *, filename: str = "", content_type: str = "") -> str:
    name = (filename or "").lower()
    if name.endswith((".txt", ".md", ".markdown")) or content_type.startswith("text/"):
        return data.decode("utf-8", errors="replace")
    # fallback: try utf-8
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return data.decode("latin-1", errors="replace")
