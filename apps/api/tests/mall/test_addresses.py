"""Default selection invalidates old versions and deletion is safely retryable."""

import pytest

from .helpers import headers, seed

PATH = "/api/v1/mall/account/addresses"
ADDRESS = {"name": "Customer", "phone": "+8613800000000", "address": "Test street"}


@pytest.mark.asyncio
async def test_default_address_version_cannot_overwrite_a_new_selection(mall_runtime):
    identity = await seed(mall_runtime)
    client = mall_runtime.client
    first = await client.post(PATH, json={**ADDRESS, "is_default": True}, headers=headers(identity))
    assert first.status_code == 200, first.text
    other = await client.post(PATH, json={**ADDRESS, "is_default": True}, headers=headers(identity))
    assert other.status_code == 200, other.text
    stale = await client.patch(PATH + "/" + first.json()["id"],
        json={**ADDRESS, "expected_version": first.json()["version"], "is_default": True},
        headers=headers(identity))
    assert stale.status_code == 409
    addresses = await client.get(PATH, headers=headers(identity))
    defaults = [row["id"] for row in addresses.json()["items"] if row["is_default"]]
    assert defaults == [other.json()["id"]]


@pytest.mark.asyncio
async def test_address_owner_and_idempotent_delete(mall_runtime):
    owner, stranger = await seed(mall_runtime), await seed(mall_runtime)
    client = mall_runtime.client
    created = await client.post(PATH, json=ADDRESS, headers=headers(owner))
    assert created.status_code == 200, created.text
    url = PATH + "/" + created.json()["id"]
    payload = {"expected_version": created.json()["version"]}
    forbidden = await client.request("DELETE", url, json=payload, headers=headers(stranger))
    assert forbidden.status_code == 404
    auth = headers(owner, key="delete-address")
    first = await client.request("DELETE", url, json=payload, headers=auth)
    again = await client.request("DELETE", url, json=payload, headers=auth)
    assert first.status_code == 200, first.text
    assert first.json() == again.json()
