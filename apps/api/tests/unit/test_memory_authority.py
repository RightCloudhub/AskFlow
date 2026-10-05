"""Stored customer facts must never substitute for authenticated business observations."""

import pytest

from app.services.agent.memory.context import with_memory
from app.services.agent.memory.facts import FactCandidate, FactStore
from tests.unit.test_service_agent import SCOPE, environment
from tests.unit.test_service_agent import store as task_store

__all__ = ["task_store"]


@pytest.mark.asyncio
async def test_customer_memory_cannot_manufacture_human_acceptance(task_store):
    facts = FactStore(task_store.sessions)
    await facts.remember(
        SCOPE,
        FactCandidate(
            key="handoff_status", value="claimed", source="customer_confirmed", confirmed=True
        ),
    )
    env = await with_memory(environment(), facts=facts)
    assert "handoff_status" not in env.facts
