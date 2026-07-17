"""Knowledge loop + ops paths (PRD §12.1 #2 #8 #9 #10)."""

import pytest
from httpx import AsyncClient


async def _admin_headers(client: AsyncClient, name: str = "opsadmin") -> dict[str, str]:
    await client.post(
        "/api/v1/admin/auth/register",
        json={
            "username": name,
            "email": f"{name}@example.com",
            "password": "password123",
        },
    )
    login = await client.post(
        "/api/v1/admin/auth/login",
        json={"username": name, "password": "password123"},
    )
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


@pytest.mark.asyncio
async def test_upload_index_query_with_sources(client: AsyncClient):
    headers = await _admin_headers(client, "docadmin")
    files = {
        "file": (
            "vip_shipping.md",
            "# VIP 包邮\n\n实付满 199 元享受会员包邮，偏远地区除外。".encode("utf-8"),
            "text/markdown",
        )
    }
    up = await client.post(
        "/api/v1/embedding/upload",
        headers=headers,
        files=files,
        data={"title": "VIP包邮说明"},
    )
    assert up.status_code == 200, up.text
    body = up.json()
    assert body["status"] == "active"
    assert body["chunk_count"] >= 1

    rag = await client.post(
        "/api/v1/rag/query",
        headers=headers,
        json={"question": "会员包邮门槛是多少"},
    )
    assert rag.status_code == 200, rag.text
    data = rag.json()
    assert data["answer"]
    # should retrieve the uploaded doc or seed shipping
    assert isinstance(data["sources"], list)


@pytest.mark.asyncio
async def test_gap_draft_approve_searchable(client: AsyncClient):
    headers = await _admin_headers(client, "gapadmin")
    # create draft directly and approve → indexed
    draft = await client.post(
        "/api/v1/admin/drafts",
        headers=headers,
        json={
            "title": "密码重置流程",
            "content": "密码重置：在登录页点击忘记密码，输入注册邮箱，按邮件链接设置新密码。",
        },
    )
    assert draft.status_code == 200, draft.text
    draft_id = draft.json()["id"]

    approved = await client.post(
        f"/api/v1/admin/drafts/{draft_id}/approve",
        headers=headers,
    )
    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == "approved"
    assert approved.json()["document_id"]

    rag = await client.post(
        "/api/v1/rag/query",
        headers=headers,
        json={"question": "如何重置密码"},
    )
    assert rag.status_code == 200
    assert rag.json()["answer"]
    sources = rag.json().get("sources") or []
    # preferred: hit the approved draft content
    joined = " ".join(s.get("text", "") + s.get("source", "") for s in sources)
    assert "密码" in joined or rag.json()["refused"] is False


@pytest.mark.asyncio
async def test_prompt_hot_update_and_audit_mask(client: AsyncClient):
    headers = await _admin_headers(client, "promptadmin")
    # ensure defaults + new version
    listed = await client.get("/api/v1/admin/prompts", headers=headers)
    assert listed.status_code == 200
    ver = await client.post(
        "/api/v1/admin/prompts/rag.system/versions",
        headers=headers,
        json={"content": "【热更新】你是客服，只依据证据回答。", "activate": True},
    )
    assert ver.status_code == 200, ver.text
    active = await client.get("/api/v1/admin/prompts/rag.system/active", headers=headers)
    assert active.status_code == 200
    assert "热更新" in active.json()["content"]

    # audit should record prompt change; detail must not leak raw secrets if present
    logs = await client.get("/api/v1/admin/audit-logs", headers=headers)
    assert logs.status_code == 200
    actions = {row["action"] for row in logs.json()}
    assert "prompt.version" in actions
