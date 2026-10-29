"""One-time target/purpose-bound codes and proofs; no credential logging."""

import hmac
import re
import secrets
from datetime import UTC, datetime, timedelta
from http import HTTPStatus

from pydantic import EmailStr, TypeAdapter, ValidationError
from sqlalchemy import select, update

from app.commerce.account.crypto import TOTP_DIGITS, TOTP_MODULUS, decrypt, digest, encrypt
from app.commerce.account.models import LoginAttempt, VerificationCode
from app.commerce.account.repository import find_identity
from app.commerce.core.constants import TOKEN_BYTES
from app.commerce.core.errors import MallError
from app.commerce.core.repository import insert_once
from app.commerce.core.schemas import utc
from app.commerce.infra.runtime import infra
from app.core.config import get_settings
from app.models.mixins import new_uuid

PHONE = re.compile(r"^\+[1-9][0-9]{7,14}$")


def normalize_target(target: str, channel: str) -> str:
    target = target.strip().lower()
    if channel == "email":
        try:
            return str(TypeAdapter(EmailStr).validate_python(target))
        except ValidationError as exc:
            raise MallError("verification_target_invalid", status=HTTPStatus.UNPROCESSABLE_ENTITY) from exc
    if not PHONE.fullmatch(target):
        raise MallError("verification_target_invalid", status=HTTPStatus.UNPROCESSABLE_ENTITY)
    return target


async def send_code(db, payload):
    target = normalize_target(payload.target, payload.channel)
    user = await find_identity(db, target)
    return await create_challenge(db, payload, target=target, user_id=user.id if user else None)


async def create_challenge(db, payload, *, target: str, user_id: str | None, deliver: bool = True):
    settings, now = get_settings(), datetime.now(UTC)
    key = digest("target:" + target)
    await reserve_send(db, key, now=now)
    challenge_id, code = new_uuid(), str(secrets.randbelow(TOTP_MODULUS)).zfill(TOTP_DIGITS)
    row = VerificationCode(id=challenge_id, user_id=user_id,
        target_hash=key, target_cipher=encrypt(target), channel=payload.channel,
        purpose=payload.purpose, code_hash=digest(challenge_id + ":" + code),
        expires_at=now + timedelta(seconds=settings.mall_verification_seconds),
        delivery_cipher=encrypt(code) if deliver else "", delivery_next_at=now,
        delivery_status="pending" if deliver else "suppressed")
    db.add(row)
    await db.flush()
    if deliver and (settings.env == "test" or settings.mall_demo_mailbox_enabled):
        infra().mailbox[challenge_id] = (row.expires_at, code)
    return {"status": "accepted", "challenge_id": challenge_id}


async def reserve_send(db, key: str, *, now: datetime):
    await insert_once(db, LoginAttempt, values={"scope": "verification", "key_hash": key},
                      unique=["scope", "key_hash"])
    changed = await db.execute(update(LoginAttempt).where(
        LoginAttempt.scope == "verification", LoginAttempt.key_hash == key,
        (LoginAttempt.locked_until.is_(None)) | (LoginAttempt.locked_until <= now))
        .values(locked_until=now + timedelta(seconds=get_settings().mall_verification_interval_seconds)))
    if changed.rowcount != 1:
        raise MallError("verification_rate_limited", status=HTTPStatus.TOO_MANY_REQUESTS)


async def verify_code(db, payload):
    row = await db.scalar(select(VerificationCode).where(VerificationCode.id == payload.challenge_id).with_for_update())
    settings = get_settings()
    if row is None or row.consumed_at or row.verified_at or utc(row.expires_at) <= datetime.now(UTC):
        raise MallError("verification_invalid", status=HTTPStatus.UNAUTHORIZED)
    if row.attempts >= settings.mall_verification_attempts:
        raise MallError("verification_invalid", status=HTTPStatus.UNAUTHORIZED)
    row.attempts += 1
    if not hmac.compare_digest(row.code_hash, digest(row.id + ":" + payload.code)):
        raise MallError("verification_invalid", status=HTTPStatus.UNAUTHORIZED, persist=True)
    proof = secrets.token_urlsafe(TOKEN_BYTES)
    row.verified_at, row.proof_hash = datetime.now(UTC), digest("proof:" + proof)
    await db.flush()
    infra().mailbox.pop(row.id, None)
    return {"verification_id": row.id, "verification_token": proof}


async def consume_proof(db, proof, *, purpose: str):
    row = await db.scalar(select(VerificationCode).where(VerificationCode.id == proof.verification_id).with_for_update())
    if row is None or row.purpose != purpose or row.verified_at is None or row.consumed_at:
        raise MallError("verification_invalid", status=HTTPStatus.UNAUTHORIZED)
    if utc(row.expires_at) <= datetime.now(UTC) or not hmac.compare_digest(row.proof_hash, digest("proof:" + proof.verification_token)):
        raise MallError("verification_invalid", status=HTTPStatus.UNAUTHORIZED)
    changed = await db.execute(update(VerificationCode).where(
        VerificationCode.id == row.id, VerificationCode.consumed_at.is_(None))
        .values(consumed_at=datetime.now(UTC)))
    if changed.rowcount != 1:
        raise MallError("verification_invalid", status=HTTPStatus.UNAUTHORIZED)
    return decrypt(row.target_cipher), row
