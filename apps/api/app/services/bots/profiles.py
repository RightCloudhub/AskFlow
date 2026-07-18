"""Multi-bot profiles: independent system prompt key + knowledge tags (PRD E18)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from app.core.config import Settings, get_settings


@dataclass
class BotProfile:
    id: str
    name: str
    system_prompt_key: str = "rag.system"
    knowledge_tags: list[str] = field(default_factory=list)
    locale: str = "zh-CN"


_DEFAULT = BotProfile(id="default", name="Default", system_prompt_key="rag.system")


def load_bot_profiles(settings: Settings | None = None) -> dict[str, BotProfile]:
    s = settings or get_settings()
    profiles: dict[str, BotProfile] = {_DEFAULT.id: _DEFAULT}
    raw = (s.bot_profiles_json or "").strip()
    if not raw:
        return profiles
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return profiles
    if not isinstance(data, list):
        return profiles
    for item in data:
        if not isinstance(item, dict) or not item.get("id"):
            continue
        bid = str(item["id"])
        profiles[bid] = BotProfile(
            id=bid,
            name=str(item.get("name") or bid),
            system_prompt_key=str(item.get("system_prompt_key") or "rag.system"),
            knowledge_tags=[str(t) for t in (item.get("knowledge_tags") or [])],
            locale=str(item.get("locale") or s.default_locale),
        )
    return profiles


def get_bot(bot_id: str | None = None, settings: Settings | None = None) -> BotProfile:
    s = settings or get_settings()
    profiles = load_bot_profiles(s)
    bid = bot_id or s.default_bot_id
    return profiles.get(bid) or profiles.get(s.default_bot_id) or _DEFAULT


def list_bots(settings: Settings | None = None) -> list[dict[str, Any]]:
    return [
        {
            "id": p.id,
            "name": p.name,
            "system_prompt_key": p.system_prompt_key,
            "knowledge_tags": p.knowledge_tags,
            "locale": p.locale,
        }
        for p in load_bot_profiles(settings).values()
    ]
