"""HTTP smoke for WeCom / DingTalk channel endpoints."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_wecom_message_pipeline(client: AsyncClient):
    resp = await client.post(
        "/api/v1/channels/wecom/events",
        json={"MsgType": "text", "FromUserName": "wx_user_1", "Content": "退货政策是什么"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body.get("errcode") == 0
    assert body.get("run_id")
    assert body.get("reply_text")


@pytest.mark.asyncio
async def test_dingtalk_message_pipeline(client: AsyncClient, monkeypatch):
    # test env allows missing secret
    monkeypatch.delenv("DINGTALK_APP_SECRET", raising=False)
    from app.core.config import get_settings

    get_settings.cache_clear()
    resp = await client.post(
        "/api/v1/channels/dingtalk/events",
        json={
            "text": {"content": "发票怎么开"},
            "senderStaffId": "dd_staff_1",
            "conversationId": "cid1",
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body.get("msgtype") == "text"
    assert body.get("text", {}).get("content")
