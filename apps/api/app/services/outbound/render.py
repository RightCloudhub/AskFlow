"""Per-channel rendering and message splitting (arch §4.1)."""

from app.services.outbound.settings import OutboundSettings

CHANNEL_LIMITS = {
    "feishu": 4000,
    "wecom": 2048,
    "dingtalk": 5000,
    "web": 4000,
    "widget": 4000,
}
SOFT_BREAK_SEARCH_RATIO = 0.5


def text_limit(channel: str, settings: OutboundSettings | None = None) -> int:
    settings = settings or OutboundSettings()
    return CHANNEL_LIMITS.get(channel, settings.default_text_limit)


def render_text(channel: str, text: str) -> str:
    """Channel rendering hook; text is the v1 format for every channel (cards later)."""
    return text


def render_parts(text: str, *, channel: str, settings: OutboundSettings | None = None) -> list[str]:
    limit = text_limit(channel, settings)
    rendered = render_text(channel, text)
    if len(rendered) <= limit:
        return [rendered]
    parts: list[str] = []
    remaining = rendered
    while len(remaining) > limit:
        cut = remaining.rfind("\n", 0, limit)
        if cut < int(limit * SOFT_BREAK_SEARCH_RATIO):
            cut = limit
        parts.append(remaining[:cut].rstrip())
        remaining = remaining[cut:].lstrip("\n")
    if remaining:
        parts.append(remaining)
    return [part for part in parts if part]
