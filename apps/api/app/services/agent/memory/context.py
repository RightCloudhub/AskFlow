"""Load optional preference data fresh each tick; do not copy it into task checkpoints."""

import asyncio
import logging
from dataclasses import replace

from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError

from app.services.agent.memory.store import PreferenceStore
from app.services.agent.service.contracts import Environment

MEMORY_READ_TIMEOUT_SECONDS = 1.0
AUTHORITY_FACT_KEYS = frozenset(
    {
        "permissions",
        "available_operations",
        "order_owners",
        "handoff_status",
        "channels",
        "inventory",
        "channel_health",
        "queue_duration",
    }
)
logger = logging.getLogger(__name__)


async def with_preferences(env: Environment, store: PreferenceStore) -> Environment:
    try:
        saved = await asyncio.wait_for(store.active(env.scope), timeout=MEMORY_READ_TIMEOUT_SECONDS)
    except (SQLAlchemyError, TimeoutError, ValidationError) as exc:
        logger.warning("Optional customer memory unavailable (%s)", type(exc).__name__)
        return replace(env, preference_status="unavailable")
    # Current-turn explicit choices win. Preference data does not modify facts or permissions.
    return replace(env, preferences={**saved, **env.preferences}, preference_status="loaded")


async def with_memory(env: Environment, *, preferences=None, facts=None) -> Environment:
    if preferences is None and facts is None:
        return env
    if preferences is not None:
        env = await with_preferences(env, preferences)
    status = "unavailable" if env.preference_status == "unavailable" else "loaded"
    if facts is None:
        return replace(env, memory_status=status)
    try:
        records = await asyncio.wait_for(facts.list(env.scope), timeout=MEMORY_READ_TIMEOUT_SECONDS)
    except (SQLAlchemyError, TimeoutError, ValidationError) as exc:
        logger.warning("Optional customer facts unavailable (%s)", type(exc).__name__)
        return replace(env, memory_status="unavailable")
    saved = {
        record.key: record.value
        for record in records
        if record.status == "active" and record.key not in AUTHORITY_FACT_KEYS
    }
    return replace(env, facts={**saved, **env.facts}, memory_status=status)
