"""Text chunker: size=500, overlap=50 (PRD §4.8)."""

from __future__ import annotations


def chunk_text(text: str, *, size: int = 500, overlap: int = 50) -> list[str]:
    body = (text or "").strip()
    if not body:
        return []
    if size <= 0:
        return [body]
    overlap = max(0, min(overlap, size - 1))
    chunks: list[str] = []
    start = 0
    n = len(body)
    while start < n:
        end = min(start + size, n)
        piece = body[start:end].strip()
        if piece:
            chunks.append(piece)
        if end >= n:
            break
        start = end - overlap
    return chunks
