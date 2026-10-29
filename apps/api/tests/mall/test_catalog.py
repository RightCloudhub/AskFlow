"""Catalog changes retain optimistic locking and authoritative checkout prices."""

import pytest

from .helpers import headers, seed

ADMIN = "/api/v1/admin/mall/catalog"
PUBLIC = "/api/v1/mall/catalog"


@pytest.mark.asyncio
async def test_product_edit_conflict_and_safe_image_keys(mall_runtime):
    operator = await seed(mall_runtime, role="admin")
    client = mall_runtime.client
    detail = await client.get(PUBLIC + "/products/" + operator["spu_id"])
    payload = {"title": "Updated product", "description": "Revised details",
               "expected_version": detail.json()["version"], "images": []}
    url = ADMIN + "/products/" + operator["spu_id"]
    unsafe = await client.put(url, json={**payload, "images": ["../../secrets.png"]},
                              headers=headers(operator))
    assert unsafe.status_code == 422
    first = await client.put(url, json=payload, headers=headers(operator))
    assert first.status_code == 200, first.text
    assert first.json()["before"]["title"] == "Fixture product"
    conflict = await client.put(url, json=payload, headers=headers(operator))
    assert conflict.status_code == 409


@pytest.mark.asyncio
async def test_image_upload_replay_and_permission(mall_runtime):
    operator = await seed(mall_runtime, role="admin")
    customer = await seed(mall_runtime)
    client = mall_runtime.client
    files = {"file": ("attempt.html", b"<script>alert(1)</script>", "image/png")}
    invalid = await client.post(ADMIN + "/images", files=files, headers=headers(operator))
    assert invalid.status_code == 422
    forbidden = await client.post(ADMIN + "/images", files=files, headers=headers(customer))
    assert forbidden.status_code == 403
    gif = bytes.fromhex("47494638396101000100800000000000ffffff21f90401000000002c"
                        "00000000010001000002024401003b")
    files = {"file": ("pixel.gif", gif, "image/gif")}
    auth = headers(operator, key="upload-pixel")
    first = await client.post(ADMIN + "/images", files=files, headers=auth)
    again = await client.post(ADMIN + "/images", files=files, headers=auth)
    assert first.status_code == 200, first.text
    assert first.json() == again.json()
    stored = await client.get("/api/v1/mall/files/" + first.json()["key"])
    assert stored.content == gif


@pytest.mark.asyncio
async def test_cached_product_cannot_override_new_price_or_visibility(mall_runtime):
    operator = await seed(mall_runtime, role="admin")
    client = mall_runtime.client
    cached = await client.get(PUBLIC + "/products/" + operator["spu_id"])
    sku = cached.json()["skus"][0]
    price = await client.put(ADMIN + "/skus/" + sku["id"] + "/price",
        json={"expected_version": sku["version"], "sale_cents": 2400, "original_cents": 2500},
        headers=headers(operator))
    assert price.status_code == 200, price.text
    items = {"items": [{"sku_id": sku["id"], "qty": 1}]}
    quote = await client.post("/api/v1/mall/order/checkout", json=items, headers=headers(operator))
    assert quote.status_code == 200, quote.text
    assert quote.json()["total_cents"] == 2400
    hidden = await client.patch(ADMIN + "/products/" + operator["spu_id"] + "/status",
        json={"expected_version": cached.json()["version"], "status": "inactive"},
        headers=headers(operator))
    assert hidden.status_code == 200, hidden.text
    order = await client.post("/api/v1/mall/order/orders",
        json={**items, "checkout_token": quote.json()["checkout_token"]}, headers=headers(operator))
    assert order.status_code == 409
