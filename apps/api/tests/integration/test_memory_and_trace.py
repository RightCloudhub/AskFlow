"""Memory side effect writes facts; facts API lists/forgets; trace ids propagate."""

import pytest

from tests.integration.test_agent_runs_api import _admin

MEMORY_URL = "/api/v1/agent/memories"


async def _chat(client, headers, content: str, *, trace_id: str | None = None):
    if trace_id:
        headers = {**headers, "x-trace-id": trace_id}
    conv = await client.post("/api/v1/chat/conversations", headers=headers, json={"title": "t"})
    conv_id = conv.json()["id"]
    return await client.post(
        f"/api/v1/chat/conversations/{conv_id}/messages", headers=headers, json={"content": content}
    )


@pytest.mark.asyncio
async def test_chat_turn_extracts_explicit_fact(client):
    headers = await _admin(client, "mem_extract")
    msg = await _chat(client, headers, "以后用英文回复我")
    assert msg.status_code == 200, msg.text
    se = msg.json()["assistant_message"]["meta"]["side_effects"]
    assert se.get("memory", {}).get("stored") == ["preferred_language"]
    listed = await client.get(MEMORY_URL, headers=headers)
    assert listed.status_code == 200
    assert {row["key"] for row in listed.json()} == {"preferred_language"}


@pytest.mark.asyncio
async def test_facts_api_forgets_with_version(client):
    headers = await _admin(client, "mem_forget")
    msg = await _chat(client, headers, "我的订单号是 ORD202401010001")
    assert msg.status_code == 200, msg.text
    listed = await client.get(MEMORY_URL, headers=headers)
    rows = {row["key"]: row for row in listed.json()}
    assert "last_order_id" in rows
    version = rows["last_order_id"]["version"]
    deleted = await client.delete(
        f"{MEMORY_URL}/last_order_id?expected_version={version}", headers=headers
    )
    assert deleted.status_code == 200
    assert deleted.json()["status"] == "deleted"
    remaining = await client.get(MEMORY_URL, headers=headers)
    assert remaining.json() == []


@pytest.mark.asyncio
async def test_trace_id_header_reaches_turn_meta(client):
    headers = await _admin(client, "trace_user")
    msg = await _chat(client, headers, "退货政策是什么？", trace_id="tr_custom_wave_d")
    assert msg.status_code == 200, msg.text
    meta = msg.json()["assistant_message"]["meta"]
    assert meta["trace_id"] == "tr_custom_wave_d"


def test_new_trace_id_prefers_request_scope():
    from app.core.trace import set_trace_id
    from app.utils.ids import new_trace_id

    set_trace_id("tr_scoped")
    try:
        assert new_trace_id() == "tr_scoped"
    finally:
        set_trace_id(None)
    assert new_trace_id().startswith("tr_")
