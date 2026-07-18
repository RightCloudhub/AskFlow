"""Multi-bot profiles (PRD E18) + runtime flags for E27/E28."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.config import get_settings
from app.core.deps import require_admin
from app.models.user import User
from app.services.agent.reasoning import reasoning_allowed_for_intent
from app.services.bots.profiles import get_bot, list_bots
from app.services.sandbox.guard import sandbox_status

router = APIRouter(dependencies=[Depends(require_admin)])


@router.get("")
async def bots_list(_user: User = Depends(require_admin)) -> dict:
    return {"bots": list_bots()}


@router.get("/runtime-flags")
async def runtime_flags(_user: User = Depends(require_admin)) -> dict:
    s = get_settings()
    return {
        "reasoning_enabled": s.reasoning_enabled,
        "reasoning_whitelist": s.reasoning_intent_whitelist,
        "sandbox": sandbox_status(),
        "sample_reasoning_product_faq": reasoning_allowed_for_intent("product_faq"),
    }


@router.get("/{bot_id}")
async def bot_get(bot_id: str, _user: User = Depends(require_admin)) -> dict:
    b = get_bot(bot_id)
    return {
        "id": b.id,
        "name": b.name,
        "system_prompt_key": b.system_prompt_key,
        "knowledge_tags": b.knowledge_tags,
        "locale": b.locale,
    }
