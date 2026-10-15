"""Deterministic control-intent rules evaluated before any model (arch §4.3 priority 1)."""

import re

CONTROL_CANCEL = "cancel"
CONTROL_HUMAN = "human"

CANCEL_PATTERNS = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"^\s*(取消|算了|不用了|不办了|停止|终止|别办了)",
        r"\b(cancel|stop|never\s?mind|abort|quit|forget\s+it)\b",
    )
)
HUMAN_PATTERNS = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"(转人工|人工客服|找客服|真人客服|人工处理)",
        r"\b(speak\s+to\s+(a\s+)?(human|agent|person)|human\s+agent|real\s+person)\b",
    )
)


def detect_control(text: str) -> str | None:
    for pattern in CANCEL_PATTERNS:
        if pattern.search(text):
            return CONTROL_CANCEL
    for pattern in HUMAN_PATTERNS:
        if pattern.search(text):
            return CONTROL_HUMAN
    return None
