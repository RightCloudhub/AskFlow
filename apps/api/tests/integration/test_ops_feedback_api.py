"""Ops-feedback P1/P3 through the API (docs/product/ops-feedback-2026-10.md)."""

import pytest
from httpx import AsyncClient

HTTP_OK = 200
GAP_REASONS = {"zero_hit", "weak_evidence"}


async def _headers(client: AsyncClient, name: str) -> dict[str, str]:
    await client.post(
        "/api/v1/admin/auth/register",
        json={"username": name, "email": f"{name}@ex.com", "password": "password123"},
    )
    login = await client.post(
        "/api/v1/admin/auth/login",
        json={"username": name, "password": "password123"},
    )
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


async def _ask(client: AsyncClient, headers: dict[str, str], content: str) -> dict:
    conv = await client.post("/api/v1/chat/conversations", headers=headers, json={"title": "t"})
    msg = await client.post(
        f"/api/v1/chat/conversations/{conv.json()['id']}/messages",
        headers=headers,
        json={"content": content},
    )
    assert msg.status_code == HTTP_OK, msg.text
    return msg.json()


@pytest.mark.asyncio
async def test_handoff_inbox_shows_usernames(client: AsyncClient):
    headers = await _headers(client, "opsfb_agent")
    assert (await _ask(client, headers, "请转人工客服处理"))["route"] == "handoff"

    queue = (await client.get("/api/v1/admin/handoffs", headers=headers)).json()
    row = next(r for r in queue if r["status"] == "queued")
    assert row["user_name"] == "opsfb_agent"
    assert row["claimed_by_name"] is None

    claim = await client.post(f"/api/v1/admin/handoffs/{row['id']}/claim", headers=headers)
    assert claim.status_code == HTTP_OK
    assert claim.json()["claimed_by_name"] == "opsfb_agent"

    claimed = next(
        r for r in (await client.get("/api/v1/admin/handoffs", headers=headers)).json()
        if r["id"] == row["id"]
    )
    assert claimed["claimed_by_name"] == "opsfb_agent"


@pytest.mark.asyncio
async def test_gap_records_real_refusal_reason(client: AsyncClient):
    headers = await _headers(client, "opsfb_gap")
    # Not covered by the test KB, so grounding refuses and a gap is recorded
    await _ask(client, headers, "礼品卡可以转赠吗？")

    gaps = (await client.get("/api/v1/admin/gaps", headers=headers)).json()
    gap = next(g for g in gaps if g["question"] == "礼品卡可以转赠吗？")
    assert gap["reason"] in GAP_REASONS
