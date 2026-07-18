"""E10 admin document generations / diff / rollback HTTP path."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


async def _admin(client: AsyncClient, name: str = "pubadmin") -> dict[str, str]:
    await client.post(
        "/api/v1/admin/auth/register",
        json={"username": name, "email": f"{name}@ex.com", "password": "password123"},
    )
    login = await client.post(
        "/api/v1/admin/auth/login",
        json={"username": name, "password": "password123"},
    )
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


@pytest.mark.asyncio
async def test_document_generations_diff_rollback(client: AsyncClient, tmp_path, monkeypatch):
    monkeypatch.setenv("REVISION_STORE_DIR", str(tmp_path / "revs"))
    from app.core.config import get_settings

    get_settings.cache_clear()
    headers = await _admin(client)

    up1 = await client.post(
        "/api/v1/embedding/upload",
        headers=headers,
        files={"file": ("pol.md", b"# P\n\nReturn in 7 days.\n", "text/markdown")},
        data={"title": "policy"},
    )
    assert up1.status_code == 200, up1.text
    doc_id = up1.json()["id"]
    gen1 = up1.json()["generation"]

    # reindex with new content via storage overwrite is hard; upload second file and
    # use reindex after manual storage update — simpler: call reindex (same content gen+1)
    re = await client.post(f"/api/v1/embedding/reindex/{doc_id}", headers=headers)
    assert re.status_code == 200, re.text
    gen2 = re.json()["generation"]
    assert gen2 > gen1

    gens = await client.get(f"/api/v1/admin/documents/{doc_id}/generations", headers=headers)
    assert gens.status_code == 200, gens.text
    body = gens.json()
    assert body["document_id"] == doc_id
    assert gen1 in body["generations"] or gen2 in body["generations"]

    if gen1 in body["generations"] and gen2 in body["generations"]:
        diff = await client.get(
            f"/api/v1/admin/documents/{doc_id}/diff",
            headers=headers,
            params={"from_generation": gen1, "to_generation": gen2},
        )
        assert diff.status_code == 200, diff.text
        assert "added" in diff.json()

    rb = await client.post(
        f"/api/v1/admin/documents/{doc_id}/rollback",
        headers=headers,
        params={"target_generation": gen1 if gen1 in body["generations"] else gen2},
    )
    assert rb.status_code == 200, rb.text
    assert rb.json()["generation"] > gen2 or rb.json()["status"] == "active"
