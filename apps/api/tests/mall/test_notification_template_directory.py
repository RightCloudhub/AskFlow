"""Template selectors return the actual latest version under notify permission."""

from http import HTTPStatus

import pytest

from .helpers import headers, seed

PATH = "/api/v1/admin/mall/notify/templates"


async def publish(runtime, identity, **changes):
    payload = {"event_type": "mall.order.paid", "locale": "zh-CN", "subject": "支付成功",
               "body": "订单已付款。", "channels": ["email"], "expected_version": 0, **changes}
    response = await runtime.client.post(PATH, headers=headers(identity), json=payload)
    assert response.status_code == HTTPStatus.OK
    return response.json()


@pytest.mark.asyncio
async def test_directory_lists_only_latest_per_event_and_language(mall_runtime):
    identity = await seed(mall_runtime, role="admin")
    await publish(mall_runtime, identity)
    latest = await publish(mall_runtime, identity, expected_version=1, subject="已收到付款")
    english = await publish(mall_runtime, identity, locale="en-US", subject="Payment received")
    response = await mall_runtime.client.get(PATH, headers=headers(identity))
    assert response.status_code == HTTPStatus.OK
    rows = response.json()["items"]
    assert {row["id"] for row in rows} == {latest["id"], english["id"]}
    chinese = next(row for row in rows if row["locale"] == "zh-CN")
    assert chinese["version"] == 2
    assert chinese["subject"] == "已收到付款"
    assert chinese["channels"] == ["email"]


@pytest.mark.asyncio
async def test_template_directory_pages_after_latest_filter(mall_runtime, monkeypatch):
    from app.commerce.notify import admin_api

    monkeypatch.setattr(admin_api, "PAGE_SIZE", 1)
    identity = await seed(mall_runtime, role="admin")
    await publish(mall_runtime, identity)
    first_template = await publish(mall_runtime, identity, expected_version=1)
    second_template = await publish(mall_runtime, identity, locale="en-US")
    first = (await mall_runtime.client.get(PATH, headers=headers(identity))).json()
    assert first["next_cursor"]
    second = (await mall_runtime.client.get(PATH, headers=headers(identity),
        params={"cursor": first["next_cursor"]})).json()
    assert {row["id"] for row in first["items"] + second["items"]} == {first_template["id"], second_template["id"]}
    assert second["next_cursor"] is None


@pytest.mark.asyncio
@pytest.mark.parametrize("role", ["user", "agent"])
async def test_template_bodies_require_notify_permission(mall_runtime, role):
    identity = await seed(mall_runtime, role=role)
    response = await mall_runtime.client.get(PATH, headers=headers(identity))
    assert response.status_code == HTTPStatus.FORBIDDEN
