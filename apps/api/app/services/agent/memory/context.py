"""Load optional preference data fresh each tick; do not copy it into task checkpoints."""

import asyncio
import logging
from dataclasses import replace

from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError

from app.services.agent.memory.store import PreferenceStore
from app.services.agent.service.contracts import Environment

MEMORY_READ_TIMEOUT_SECONDS = 1.0
logger = logging.getLogger(__name__)


async def with_preferences(env: Environment, store: PreferenceStore) -> Environment:
    try:
        saved = await asyncio.wait_for(store.active(env.scope), timeout=MEMORY_READ_TIMEOUT_SECONDS)
    except (SQLAlchemyError, TimeoutError, ValidationError) as exc:
        logger.warning("Optional customer memory unavailable (%s)", type(exc).__name__)
        return replace(env, preference_status="unavailable")
    # Current-turn explicit choices win. Preference data does not modify facts or permissions.
    return replace(env, preferences={**saved, **env.preferences}, preference_status="loaded")
