"""HTTP account fixtures exercise verification, registration and real login."""

from uuid import uuid4

PASSWORD = "Fixture-Strong1!Password"
PREFIX = "/api/v1/mall/account"


async def proof(runtime, target, *, channel="email", purpose="register"):
    sent = await runtime.client.post(PREFIX + "/verification/send", json={
        "target": target, "channel": channel, "purpose": purpose})
    assert sent.status_code == 200, sent.text
    return await verify_challenge(runtime, sent.json()["challenge_id"])


async def verify_challenge(runtime, challenge_id):
    mailbox = await runtime.client.get(PREFIX + "/verification/demo/" + challenge_id)
    assert mailbox.status_code == 200, mailbox.text
    checked = await runtime.client.post(PREFIX + "/verification/verify", json={
        "challenge_id": challenge_id, "code": mailbox.json()["code"]})
    assert checked.status_code == 200, checked.text
    return checked.json()


async def register_customer(runtime, *, target=None, channel="email"):
    username = "customer_" + uuid4().hex
    target = target or username + "@example.com"
    verified = await proof(runtime, target, channel=channel)
    response = await runtime.client.post(PREFIX + "/register", headers={"Idempotency-Key": str(uuid4())},
        json={"username": username, "password": PASSWORD, **verified})
    assert response.status_code == 202, response.text
    identity = await login_customer(runtime, target)
    profile = await runtime.client.get(PREFIX + "/profile", headers=authorization(identity))
    assert profile.status_code == 200, profile.text
    return {**identity, "user_id": profile.json()["id"], "username": username, "target": target}


async def login_customer(runtime, identifier, *, password=PASSWORD, recovery_code="", totp=""):
    response = await runtime.client.post(PREFIX + "/login", json={
        "identifier": identifier, "password": password, "recovery_code": recovery_code, "totp": totp})
    assert response.status_code == 200, response.text
    return {**response.json(), "refresh_token": response.cookies.get("mall_refresh")}


def authorization(identity):
    return {"Authorization": "Bearer " + identity["access_token"], "Idempotency-Key": str(uuid4())}
