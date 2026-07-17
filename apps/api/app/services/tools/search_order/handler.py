"""search_order tool — webhook with mock fallback (PRD §4.4.1)."""

from __future__ import annotations

from typing import Any

import httpx

from app.core.config import get_settings


async def search_order(arguments: dict[str, Any]) -> dict[str, Any]:
    order_id = str(arguments.get("order_id") or "").strip()
    if not order_id:
        return {
            "status": "error",
            "error_class": "bad_params",
            "message": "缺少订单号",
        }

    settings = get_settings()
    if not settings.order_lookup_url:
        return _mock(order_id, reason="ORDER_LOOKUP_URL not configured")

    try:
        headers = {}
        if settings.order_lookup_token:
            headers["Authorization"] = f"Bearer {settings.order_lookup_token}"
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                settings.order_lookup_url,
                params={"order_id": order_id},
                headers=headers,
            )
        if resp.status_code >= 500:
            return _mock(order_id, reason=f"upstream_{resp.status_code}")
        if resp.status_code >= 400:
            return {
                "status": "error",
                "error_class": "http_4xx",
                "message": f"订单查询失败: HTTP {resp.status_code}",
            }
        data = resp.json()
        return {
            "status": "ok",
            "data_source": "webhook",
            "order_id": order_id,
            "data": data,
        }
    except httpx.TimeoutException:
        return _mock(order_id, reason="timeout")
    except Exception as exc:
        return _mock(order_id, reason=str(exc))


def _mock(order_id: str, *, reason: str) -> dict[str, Any]:
    return {
        "status": "mock",
        "data_source": "mock",
        "order_id": order_id,
        "mock_reason": reason,
        "data": {
            "status": "shipped",
            "tracking": f"SF{order_id[-8:].upper()}",
            "eta": "预计 2 日内送达",
            "carrier": "顺丰速运",
        },
    }
