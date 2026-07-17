"""Metadata merge-patch helper (PRD §6.3 red-line)."""

from __future__ import annotations

from typing import Any


def merge_patch(base: dict[str, Any] | None, patch: dict[str, Any] | None) -> dict[str, Any]:
    """RFC7396-like merge: nested dicts merge; None deletes key; scalars overwrite."""
    result: dict[str, Any] = dict(base or {})
    if not patch:
        return result
    for key, value in patch.items():
        if value is None:
            result.pop(key, None)
        elif isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = merge_patch(result[key], value)
        else:
            result[key] = value
    return result
