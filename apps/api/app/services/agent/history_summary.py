"""Mid-session history compression (PRD E26) — extractive, offline-safe."""

from __future__ import annotations

from app.core.config import Settings, get_settings
from app.middleware.metrics import HISTORY_SUMMARY_TOTAL

SUMMARY_ROLE = "system"
SUMMARY_PREFIX = "[会话摘要] "
# Max chars per older turn in the summary block
TURN_SNIPPET_MAX = 120
SUMMARY_BODY_MAX = 1500


def compress_history(
    history: list[dict[str, str]],
    *,
    settings: Settings | None = None,
) -> tuple[list[dict[str, str]], bool]:
    """If history is long, fold older turns into one system summary + keep recent.

    Returns (new_history, did_compress).
    """
    s = settings or get_settings()
    threshold = s.history_summary_threshold
    keep = max(1, s.history_summary_keep_recent)
    if len(history) <= threshold:
        return history, False

    older = history[: -keep]
    recent = history[-keep:]
    body = _build_summary_body(older)
    summary_msg = {"role": SUMMARY_ROLE, "content": f"{SUMMARY_PREFIX}{body}"}
    HISTORY_SUMMARY_TOTAL.inc()
    return [summary_msg, *recent], True


def _build_summary_body(turns: list[dict[str, str]]) -> str:
    lines: list[str] = []
    for t in turns:
        role = t.get("role", "?")
        content = (t.get("content") or "").replace("\n", " ").strip()
        if len(content) > TURN_SNIPPET_MAX:
            content = content[:TURN_SNIPPET_MAX] + "…"
        lines.append(f"{role}: {content}")
    body = " | ".join(lines)
    if len(body) > SUMMARY_BODY_MAX:
        body = body[:SUMMARY_BODY_MAX] + "…"
    return body
