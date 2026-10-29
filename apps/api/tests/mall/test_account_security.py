"""Real account HTTP flows and anti-enumeration/security regressions."""

import asyncio
import time
from datetime import UTC, datetime, timedelta
from statistics import mean

import pytest
from sqlalchemy import select, update

from app.commerce.account.models import UserSession, VerificationCode
from app.commerce.account.sessions import rotate
from app.commerce.core.errors import MallError
from app.core.config import get_settings

from .account_helpers import (
    PASSWORD,
    PREFIX,
    authorization,
    login_customer,
    register_customer,
    verify_challenge,
)
from .helpers import transaction


@pytest.mark.parametrize("channel,target", [("email", "reset@example.com"), ("sms", "+8613912345678")])
async def test_registered_email_and_phone_can_reset(mall_runtime, monkeypatch, *, channel, target):
    monkeypatch.setenv("MALL_VERIFICATION_INTERVAL_SECONDS", "1")
    get_settings.cache_clear()
    identity = await register_customer(mall_runtime, target=target, channel=channel)
    await asyncio.sleep(1)
    response = await mall_runtime.client.post(PREFIX + "/password/forgot", json={"identifier": identity["username"]})
    assert response.status_code == 200, response.text
    challenge_id = response.json()["challenge_id"]
    async with mall_runtime.sessions() as db:
        challenge = await db.get(VerificationCode, challenge_id)
        assert challenge.channel == channel
        assert challenge.delivery_status == "pending"
    proof = await verify_challenge(mall_runtime, challenge_id)
    new_password = PASSWORD + "-new"
    reset = await mall_runtime.client.post(PREFIX + "/password/reset", json={**proof, "new_password": new_password})
    assert reset.status_code == 200, reset.text
    profile = await mall_runtime.client.get(PREFIX + "/profile", headers=authorization(identity))
    assert profile.status_code == 401
    await login_customer(mall_runtime, target, password=new_password)
    replay = await mall_runtime.client.post(PREFIX + "/password/reset", json={**proof, "new_password": new_password})
    assert replay.status_code == 401


async def test_forgot_enumeration_response_and_latency(mall_runtime, monkeypatch, record_property):
    monkeypatch.setenv("MALL_LOGIN_MIN_SECONDS", "0.08")
    get_settings.cache_clear()
    known = await register_customer(mall_runtime)
    phone = await register_customer(mall_runtime, target="+8613987654321", channel="sms")
    measurements = {}
    for target in (known["username"], phone["username"], "missing-customer"):
        samples = []
        for _ in range(3):
            started = time.perf_counter()
            response = await mall_runtime.client.post(PREFIX + "/password/forgot", json={"identifier": target})
            samples.append(time.perf_counter() - started)
            assert response.status_code == 200
            assert set(response.json()) == {"status", "challenge_id"}
            assert response.json()["status"] == "accepted"
        measurements[target] = mean(samples)
    assert min(measurements.values()) >= 0.08
    assert max(measurements.values()) - min(measurements.values()) < 0.06
    record_property("forgot_mean_seconds", str(measurements))


@pytest.mark.parametrize("expired", [True, False])
async def test_verification_expiration_and_attempt_exhaustion(mall_runtime, expired):
    sent = await mall_runtime.client.post(PREFIX + "/verification/send", json={
        "target": "verify@example.com", "channel": "email", "purpose": "register"})
    challenge_id = sent.json()["challenge_id"]
    mailbox = await mall_runtime.client.get(PREFIX + "/verification/demo/" + challenge_id)
    code = mailbox.json()["code"]
    if expired:
        async with mall_runtime.sessions() as db:
            await db.execute(update(VerificationCode).where(VerificationCode.id == challenge_id)
                .values(expires_at=datetime.now(UTC) - timedelta(seconds=1)))
            await db.commit()
    else:
        wrong = "000000" if code != "000000" else "111111"
        for _ in range(get_settings().mall_verification_attempts):
            response = await mall_runtime.client.post(PREFIX + "/verification/verify", json={
                "challenge_id": challenge_id, "code": wrong})
            assert response.status_code == 401
    final = await mall_runtime.client.post(PREFIX + "/verification/verify", json={"challenge_id": challenge_id, "code": code})
    assert final.status_code == 401


async def test_concurrent_refresh_revokes_entire_family(mall_runtime):
    identity = await register_customer(mall_runtime)

    async def refresh():
        try:
            result = await transaction(mall_runtime, lambda db: rotate(db, identity["refresh_token"]))
            return result
        except MallError as exc:
            assert exc.status == 401
            return None

    outcomes = await asyncio.gather(refresh(), refresh())
    assert sum(item is not None for item in outcomes) == 1
    async with mall_runtime.sessions() as db:
        sessions = list(await db.scalars(select(UserSession).where(UserSession.user_id == identity["user_id"])))
        assert len(sessions) == 2
        assert all(item.revoked_at for item in sessions)
    winner = next(item for item in outcomes if item is not None)
    response = await mall_runtime.client.get(PREFIX + "/profile", headers=authorization(winner))
    assert response.status_code == 401
