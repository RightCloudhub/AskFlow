"""P5 (M6): customer facts pass a verification gate and never store secrets."""

from datetime import UTC, datetime, timedelta

import pytest

from app.services.agent.memory.facts import FactCandidate, FactStore, MemoryRejected
from app.services.agent.memory.store import MemoryConflict
from tests.unit.test_service_agent import SCOPE
from tests.unit.test_service_agent import store as task_store

__all__ = ["task_store"]

ADDRESS_KEY = "preferred_address"
ADDRESS_VALUE = "上海市浦东新区"
BEIJING_VALUE = "北京市朝阳区"
MONEY_KEY = "refund_account"
LONG_DIGITS = "4111111111111111"
EXPIRED_MINUTES_AGO = -1


@pytest.mark.asyncio
async def test_model_inferred_fact_is_rejected(task_store):
    facts = FactStore(task_store.sessions)
    with pytest.raises(MemoryRejected):
        await facts.remember(
            SCOPE, FactCandidate(key=ADDRESS_KEY, value=ADDRESS_VALUE, source="model_inferred")
        )


@pytest.mark.asyncio
async def test_money_fact_requires_explicit_confirmation(task_store):
    facts = FactStore(task_store.sessions)
    with pytest.raises(MemoryRejected):
        await facts.remember(
            SCOPE, FactCandidate(key=MONEY_KEY, value="尾号 6222", source="customer_stated")
        )
    record = await facts.remember(
        SCOPE,
        FactCandidate(key=MONEY_KEY, value="尾号 6222", source="customer_stated", confirmed=True),
    )
    assert record.verification == "confirmed"


@pytest.mark.asyncio
async def test_system_fact_requires_receipt(task_store):
    facts = FactStore(task_store.sessions)
    with pytest.raises(MemoryRejected):
        await facts.remember(
            SCOPE, FactCandidate(key="order_status_seen", value="shipped", source="system_observed")
        )
    record = await facts.remember(
        SCOPE,
        FactCandidate(
            key="order_status_seen",
            value="shipped",
            source="system_observed",
            receipt_ref="order:ORD202401010001",
        ),
    )
    assert record.verification == "observed"


@pytest.mark.asyncio
async def test_credentials_are_never_stored(task_store):
    facts = FactStore(task_store.sessions)
    with pytest.raises(MemoryRejected):
        await facts.remember(
            SCOPE, FactCandidate(key="card_number", value="尾号 4242", source="customer_stated")
        )
    with pytest.raises(MemoryRejected):
        await facts.remember(
            SCOPE, FactCandidate(key="shipping_note", value=LONG_DIGITS, source="customer_stated")
        )


@pytest.mark.asyncio
async def test_fact_versioning_supersedes_previous_value(task_store):
    facts = FactStore(task_store.sessions)
    first = await facts.remember(
        SCOPE,
        FactCandidate(
            key=ADDRESS_KEY, value=ADDRESS_VALUE, source="customer_confirmed", confirmed=True
        ),
    )
    second = await facts.remember(
        SCOPE,
        FactCandidate(
            key=ADDRESS_KEY, value=BEIJING_VALUE, source="customer_confirmed", confirmed=True
        ),
        expected_version=first.version,
    )
    assert second.version == first.version + 1
    current = await facts.get(SCOPE, ADDRESS_KEY)
    assert current.value == BEIJING_VALUE
    with pytest.raises(MemoryConflict):
        await facts.remember(
            SCOPE,
            FactCandidate(
                key=ADDRESS_KEY, value="广州市天河区", source="customer_confirmed", confirmed=True
            ),
            expected_version=first.version,
        )


@pytest.mark.asyncio
async def test_expired_fact_is_not_returned(task_store):
    facts = FactStore(task_store.sessions)
    expired_at = datetime.now(UTC) + timedelta(minutes=EXPIRED_MINUTES_AGO)
    await facts.remember(
        SCOPE,
        FactCandidate(
            key=ADDRESS_KEY,
            value=ADDRESS_VALUE,
            source="customer_confirmed",
            confirmed=True,
            valid_until=expired_at,
        ),
    )
    assert await facts.list(SCOPE) == []
    record = await facts.get(SCOPE, ADDRESS_KEY)
    assert record.status == "expired"


@pytest.mark.asyncio
async def test_deletion_erases_value_and_blocks_stale_write(task_store):
    facts = FactStore(task_store.sessions)
    first = await facts.remember(
        SCOPE,
        FactCandidate(
            key=ADDRESS_KEY, value=ADDRESS_VALUE, source="customer_confirmed", confirmed=True
        ),
    )
    deleted = await facts.delete(SCOPE, ADDRESS_KEY, expected_version=first.version)
    assert deleted.value is None
    assert await facts.list(SCOPE) == []
    with pytest.raises(MemoryConflict):
        await facts.remember(
            SCOPE,
            FactCandidate(
                key=ADDRESS_KEY, value=BEIJING_VALUE, source="customer_confirmed", confirmed=True
            ),
        )
    restored = await facts.remember(
        SCOPE,
        FactCandidate(
            key=ADDRESS_KEY, value=BEIJING_VALUE, source="customer_confirmed", confirmed=True
        ),
        expected_version=deleted.version,
    )
    assert restored.version == deleted.version + 1
