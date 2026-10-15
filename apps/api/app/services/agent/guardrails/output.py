"""Output guardrails: policy commitments and prompt leakage before send (arch §4.10)."""

import re

FLAG_POLICY = "output_policy_stripped"
FLAG_LEAK = "output_leak_redacted"
SAFE_FALLBACK = "抱歉，我无法提供该信息。如需帮助请回复「转人工」。"
LEAK_PLACEHOLDER = "…"

# Commitments beyond policy: the bot may not promise refunds or outcomes (arch §9.2 step 8).
COMMITMENT_PATTERNS = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"保证(全额)?退款",
        r"一定(会|能)?(全额)?退款",
        r"百分百(保证|退款|成功)",
        r"100%\s*(保证|退款|成功)",
        r"guaranteed?\s+(full\s+)?refund",
        r"guarantee[ds]?\s+you\s+(a\s+)?(full\s+)?refund",
    )
)
# Leak markers: system-prompt echoes and instruction text must never reach the user.
LEAK_MARKERS = (
    "system prompt",
    "系统提示词",
    "你是企业智能客服助手",
    "ignore previous instructions",
    "忽略以上指令",
)
SENTENCE_SPLIT = re.compile(r"(?<=[。！？!?\n])")


def review_output(text: str) -> tuple[str, list[str]]:
    """Strip policy-violating sentences and redact leaked prompt markers."""
    cleaned, policy_hit = _strip_policy(text)
    cleaned, leak_hit = _redact_leaks(cleaned)
    flags: list[str] = []
    if policy_hit:
        flags.append(FLAG_POLICY)
    if leak_hit:
        flags.append(FLAG_LEAK)
    if policy_hit and not cleaned.strip():
        cleaned = SAFE_FALLBACK
    return cleaned, flags


def _strip_policy(text: str) -> tuple[str, bool]:
    kept: list[str] = []
    hit = False
    for sentence in SENTENCE_SPLIT.split(text):
        if sentence and any(pattern.search(sentence) for pattern in COMMITMENT_PATTERNS):
            hit = True
            continue
        kept.append(sentence)
    return "".join(kept).strip(), hit


def _redact_leaks(text: str) -> tuple[str, bool]:
    cleaned = text
    hit = False
    for marker in LEAK_MARKERS:
        if marker.lower() in cleaned.lower():
            hit = True
            cleaned = re.sub(re.escape(marker), LEAK_PLACEHOLDER, cleaned, flags=re.IGNORECASE)
    return cleaned, hit
