"""Refresh-family replay detection and verification-code concurrency."""

import asyncio

import pytest
from sqlalchemy import select

from app.commerce.account.models import UserSession, VerificationCode
from app.commerce.account.schemas import VerificationSend
from app.commerce.account.sessions import rotate
from app.commerce.account.verification import send_code
from app.commerce.core.errors import MallError

from .helpers import headers, seed, transaction


@pytest.mark.asyncio
async def test_refresh_replay_revokes_descendants(mall_runtime):
    identity = await seed(mall_runtime)
    newer = await transaction(mall_runtime, lambda db: rotate(db, identity["refresh_token"]))
    with pytest.raises(MallError):
        await transaction(mall_runtime, lambda db: rotate(db, identity["refresh_token"]))
    with pytest.raises(MallError):
        await transaction(mall_runtime, lambda db: rotate(db, newer["refresh_token"]))
    async with mall_runtime.sessions() as db:
        assert all(row.revoked_at for row in await db.scalars(select(UserSession)))
    response = await mall_runtime.client.get("/api/v1/mall/account/profile", headers=headers(newer))
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_verification_send_window_is_atomic(mall_runtime):
    payload = VerificationSend(target="customer@example.com", channel="email", purpose="register")

    async def send():
        try:
            await transaction(mall_runtime, lambda db: send_code(db, payload))
            return True
        except MallError as exc:
            assert exc.code == "verification_rate_limited"
            return False

    assert sum(await asyncio.gather(*(send() for _ in range(10)))) == 1
    async with mall_runtime.sessions() as db:
        assert len(list(await db.scalars(select(VerificationCode)))) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("operation", ["logout", "revoke-device"])
async def test_old_access_session_revokes_rotated_family(mall_runtime, operation):
    identity = await seed(mall_runtime)
    newer = await transaction(mall_runtime, lambda db: rotate(db, identity["refresh_token"]))
    response = await mall_runtime.client.get("/api/v1/mall/account/sessions", headers=headers(newer))
    assert response.status_code == 200
    devices = response.json()["items"]
    assert len(devices) == 1
    if operation == "logout":
        response = await mall_runtime.client.post("/api/v1/mall/account/logout", headers=headers(identity))
    else:
        response = await mall_runtime.client.delete(
            "/api/v1/mall/account/sessions/" + devices[0]["id"], headers=headers(identity))
    assert response.status_code == 200
    await assert_access_rejected(mall_runtime, (identity, newer))
    with pytest.raises(MallError):
        await transaction(mall_runtime, lambda db: rotate(db, newer["refresh_token"]))


async def assert_access_rejected(runtime, identities):
    for identity in identities:
        response = await runtime.client.get("/api/v1/mall/account/profile", headers=headers(identity))
        assert response.status_code == 401
