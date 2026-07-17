"""Inline citation [n] self-check against sources[].index."""

from __future__ import annotations

import re
from typing import Any

CITE_RE = re.compile(r"\[(\d+)\]")


def verify_citations(answer: str, sources: list[dict[str, Any]]) -> dict[str, Any]:
    valid_indexes = {int(s.get("index", 0)) for s in sources}
    found = [int(m.group(1)) for m in CITE_RE.finditer(answer or "")]
    oob = [n for n in found if n not in valid_indexes]
    return {
        "result": "oob" if oob else "ok",
        "citations": found,
        "oob": oob,
        "valid_indexes": sorted(valid_indexes),
    }
