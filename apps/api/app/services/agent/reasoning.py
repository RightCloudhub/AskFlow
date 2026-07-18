"""Extended reasoning budget gate (PRD E27) — default OFF."""

from __future__ import annotations

from app.core.config import Settings, get_settings


def reasoning_allowed_for_intent(intent: str | None, settings: Settings | None = None) -> bool:
    s = settings or get_settings()
    if not s.reasoning_enabled:
        return False
    if not intent:
        return False
    allowed = {p.strip() for p in s.reasoning_intent_whitelist.split(",") if p.strip()}
    return intent in allowed


def reasoning_extra_steps(intent: str | None, settings: Settings | None = None) -> int:
    s = settings or get_settings()
    if not reasoning_allowed_for_intent(intent, s):
        return 0
    return max(0, int(s.reasoning_max_steps))
