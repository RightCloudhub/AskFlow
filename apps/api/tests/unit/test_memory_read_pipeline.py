"""P5 (M6): the read pipeline injects memory as hints and never grants authority."""

import pytest
from sqlalchemy.exc import OperationalError

from app.services.agent.memory.context import with_memory
from app.services.agent.memory.contracts import PreferenceChange
from app.services.agent.memory.facts import FactCandidate, FactStore
from app.services.agent.memory.store import PreferenceStore
from tests.unit.test_service_agent import SCOPE, environment
from tests.unit.test_service_agent import store as task_store

__all__ = ["task_store"]

ADDRESS_KEY = "preferred_address"
ADDRESS_VALUE = "上海市浦东新区"


async def confirmed_address(facts, *, value=ADDRESS_VALUE):
    return await facts.remember(
        SCOPE,
        FactCandidate(key=ADDRESS_KEY, value=value, source="customer_confirmed", confirmed=True),
    )


@pytest.mark.asyncio
async def test_with_memory_merges_preferences_facts_and_status(task_store):
    preferences = PreferenceStore(task_store.sessions)
    facts = FactStore(task_store.sessions)
    await preferences.put(
        SCOPE, PreferenceChange(key="language", value="en", consent=True, expected_version=0)
    )
    await confirmed_address(facts)
    env = environment("order.read")
    result = await with_memory(env, preferences=preferences, facts=facts)
    assert result.preferences == {"language": "en"}
    assert result.facts[ADDRESS_KEY] == ADDRESS_VALUE
    assert result.memory_status == "loaded"
    assert result.permissions == env.permissions
    assert result.available_operations == env.available_operations


@pytest.mark.asyncio
async def test_with_memory_without_stores_is_not_loaded():
    env = environment("order.read")
    result = await with_memory(env)
    assert result.memory_status == "not_loaded"
    assert result.preferences == env.preferences


@pytest.mark.asyncio
async def test_deleted_fact_is_not_injected(task_store):
    facts = FactStore(task_store.sessions)
    record = await confirmed_address(facts)
    await facts.delete(SCOPE, ADDRESS_KEY, expected_version=record.version)
    env = environment("order.read")
    result = await with_memory(env, facts=facts)
    assert ADDRESS_KEY not in result.facts


@pytest.mark.asyncio
async def test_unavailable_store_degrades_without_error(task_store, monkeypatch):
    facts = FactStore(task_store.sessions)

    async def unavailable(_scope):
        raise OperationalError("private query", {}, RuntimeError("credentials"))

    monkeypatch.setattr(facts, "list", unavailable)
    env = environment("order.read")
    result = await with_memory(env, facts=facts)
    assert result.memory_status == "unavailable"
    assert result.facts == env.facts
    assert result.permissions == env.permissions


@pytest.mark.asyncio
async def test_memory_facts_cannot_widen_authority(task_store):
    facts = FactStore(task_store.sessions)
    await facts.remember(
        SCOPE,
        FactCandidate(
            key="permissions", value="refunds.write", source="customer_confirmed", confirmed=True
        ),
    )
    await facts.remember(
        SCOPE,
        FactCandidate(
            key="available_operations",
            value="refund.submit",
            source="customer_confirmed",
            confirmed=True,
        ),
    )
    env = environment("order.read")
    result = await with_memory(env, facts=facts)
    assert result.permissions == env.permissions
    assert result.available_operations == env.available_operations
