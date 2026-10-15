"""Retrieved documents and tool output are data, never instructions (arch §4.7 / §4.10)."""

import re

BEGIN_MARKER = "«SOURCE»"
END_MARKER = "«/SOURCE»"
STRIP_MARK = "[已移除指令性内容]"
UNTRUSTED_MAX_CHARS = 2000
FIELD_MAX_CHARS = 200

INSTRUCTION_LINE = re.compile(
    r"(ignore\s+(all\s+)?previous|忽略(以上|上述|之前)|system\s*[:：]|assistant\s*[:：]"
    r"|developer\s*[:：]|you are now|从现在开始你是|new instructions)",
    re.IGNORECASE,
)


def sanitize_untrusted(text: str, *, max_chars: int = UNTRUSTED_MAX_CHARS) -> str:
    """Drop instruction-like lines and bound the length of externally sourced text."""
    lines = [
        STRIP_MARK if INSTRUCTION_LINE.search(line) else line
        for line in (text or "").splitlines()
    ]
    return "\n".join(lines)[:max_chars]


def wrap_untrusted(text: str, *, max_chars: int = UNTRUSTED_MAX_CHARS) -> str:
    """Delimit sanitized external text so the model treats it as quoted data."""
    return f"{BEGIN_MARKER}\n{sanitize_untrusted(text, max_chars=max_chars)}\n{END_MARKER}"
