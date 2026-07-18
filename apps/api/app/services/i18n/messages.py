"""Minimal i18n message catalog (PRD E17)."""

from __future__ import annotations

from app.core.config import get_settings

# locale → key → text
CATALOG: dict[str, dict[str, str]] = {
    "zh-CN": {
        "refuse.weak": "根据现有知识库，我无法确信地回答该问题。",
        "refuse.zero": "知识库中没有找到与该问题相关的资料，我无法编造答案。",
        "refuse.oos": "该问题超出本客服助手的业务范围。",
        "cancelled": "生成已取消。",
        "attachment_received": "已收到附件，将结合文字说明处理。",
    },
    "en-US": {
        "refuse.weak": "I cannot answer confidently from the knowledge base.",
        "refuse.zero": "No relevant knowledge found; I will not invent an answer.",
        "refuse.oos": "This question is outside the assistant's supported domain.",
        "cancelled": "Generation cancelled.",
        "attachment_received": "Attachment received; will use it with your text.",
    },
}

DEFAULT_LOCALE = "zh-CN"


def normalize_locale(locale: str | None) -> str:
    if not locale:
        return get_settings().default_locale or DEFAULT_LOCALE
    loc = locale.replace("_", "-").strip()
    if loc in CATALOG:
        return loc
    base = loc.split("-")[0].lower()
    for key in CATALOG:
        if key.lower().startswith(base):
            return key
    return DEFAULT_LOCALE


def t(key: str, locale: str | None = None) -> str:
    loc = normalize_locale(locale)
    bucket = CATALOG.get(loc) or CATALOG[DEFAULT_LOCALE]
    return bucket.get(key) or CATALOG[DEFAULT_LOCALE].get(key) or key
