"""Customer task projections, pagination, cancellation and staff takeover boundaries."""

import pytest

from app.core import database
from app.models.handoff import HandoffSession
from app.services.agent.identity import customer_scope
from app.services.agent.service.store import TaskStore
from tests.integration.test_agent_runs_api import _admin
from tests.unit.test_service_agent import task

URL = "/api/v1/agent/tasks"
STAFF_URL = "/api/v1/admin/service-tasks"


async def seed_task(client, headers):
    user = (await client.get("/api/v1/admin/auth/me", headers=headers)).json()
    original = task()
    original.scope = customer_scope(user["id"])
    original.inputs = {"private_internal_value": "must not be exposed"}
    original.conversation_id = "conversation"
    await TaskStore(database.SessionLocal).create(original)
    return original


@pytest.mark.asyncio
async def test_customer_task_scope_and_projection(client):
    assert (await client.get(URL)).status_code == 401
    alice = await _admin(client, "tasks_alice")
    bob = await _admin(client, "tasks_bob")
    original = await seed_task(client, alice)
    detail = await client.get(f"{URL}/{original.task_id}", headers=alice)
    assert detail.status_code == 200
    assert "private_internal_value" not in detail.text
    assert "ledger" not in detail.json()
    assert (await client.get(URL, headers=bob)).json()["items"] == []
    assert (await client.get(f"{URL}/{original.task_id}", headers=bob)).status_code == 404
    denied = await client.post(f"{URL}/{original.task_id}/cancel", headers=bob,
                               json={"expected_version": 0, "reason": "cancel"})
    assert denied.status_code == 404


@pytest.mark.asyncio
async def test_customer_cancellation_requires_current_version(client):
    headers = await _admin(client, "tasks_cancel")
    original = await seed_task(client, headers)
    endpoint = f"{URL}/{original.task_id}/cancel"
    invalid = await client.post(endpoint, headers=headers,
                                json={"expected_version": 1, "reason": "cancel"})
    assert invalid.status_code == 409
    cancelled = await client.post(endpoint, headers=headers,
                                  json={"expected_version": 0, "reason": "No longer needed"})
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "closed_unresolved"
    assert cancelled.json()["version"] == 1


@pytest.mark.asyncio
async def test_task_pagination_has_no_cross_customer_items(client):
    headers = await _admin(client, "tasks_pages")
    originals = [await seed_task(client, headers) for _ in range(3)]
    page = (await client.get(URL, headers=headers, params={"limit": 2})).json()
    rest = (await client.get(URL, headers=headers,
                             params={"limit": 2, "after": page["next_cursor"]})).json()
    returned = [item["task_id"] for item in page["items"] + rest["items"]]
    assert returned == sorted(original.task_id for original in originals)
    assert rest["next_cursor"] is None


@pytest.mark.asyncio
async def test_staff_takeover_uses_claimed_handoff_identity(client):
    staff = await _admin(client, "tasks_staff")
    customer = await _admin(client, "tasks_customer")
    staff_user = (await client.get("/api/v1/admin/auth/me", headers=staff)).json()
    original = await seed_task(client, customer)
    async with database.SessionLocal.begin() as db:
        handoff = HandoffSession(user_id=original.scope.customer_id,
                                 conversation_id=original.conversation_id, status="claimed",
                                 claimed_by=staff_user["id"])
        db.add(handoff)
        await db.flush()
        handoff_id = handoff.id
    endpoint = f"{STAFF_URL}/{original.task_id}/accept-handoff"
    payload = {"expected_version": 0, "handoff_id": handoff_id}
    assert (await client.post(endpoint, headers=customer, json=payload)).status_code == 403
    accepted = await client.post(endpoint, headers=staff, json=payload)
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["status"] == "handed_off"
    assert (await client.post(endpoint, headers=staff, json=payload)).status_code == 409
