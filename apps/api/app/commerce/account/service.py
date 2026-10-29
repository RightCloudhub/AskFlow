"""Account workflows reuse users and persist all security changes together."""

import asyncio
import time
from http import HTTPStatus

from app.commerce.account.crypto import digest, encrypt
from app.commerce.account.hooks import password_policy
from app.commerce.account.mfa import verify_factor
from app.commerce.account.repository import find_identity, profile_for, security_for
from app.commerce.account.sessions import issue_session, revoke_all
from app.commerce.account.throttle import attempts, failed, succeeded
from app.commerce.account.verification import consume_proof
from app.commerce.core.audit import audit
from app.commerce.core.errors import MallError
from app.commerce.core.events import publish
from app.commerce.core.repository import insert_once
from app.core.config import get_settings
from app.models.mixins import new_uuid
from app.models.user import User
from app.services.auth.password import dummy_hash, hash_password, needs_rehash, verify_password


class AccountService:
    def __init__(self, db):
        self.db = db

    async def register(self, payload, *, ip: str = ""):
        if not get_settings().mall_register_allowed():
            raise MallError("registration_disabled", status=HTTPStatus.FORBIDDEN)
        await password_policy(payload.password)
        target, proof = await consume_proof(self.db, payload, purpose="register")
        existing = await find_identity(self.db, payload.username) or await find_identity(self.db, target)
        hashed = await asyncio.to_thread(hash_password, payload.password)
        if existing:
            return {"status": "accepted"}
        # Non-delivery identity marker keeps the legacy non-null unique column intact.
        # Actual SMS delivery always resolves the verified profile phone.
        email = target if proof.channel == "email" else "phone:" + digest("target:" + target)
        user_id = new_uuid()
        created = await insert_once(self.db, User, values={"id": user_id,
            "username": payload.username.strip().lower(), "email": email, "hashed_password": hashed, "role": "user"})
        if not created:
            return {"status": "accepted"}
        user = await self.db.get(User, user_id)
        profile, security = await profile_for(self.db, user.id), await security_for(self.db, user.id)
        if proof.channel == "email":
            security.email_verified = True
        else:
            profile.phone_cipher, profile.phone_hash = encrypt(target), digest("target:" + target)
            security.phone_verified = True
        await publish(self.db, profile, event_type="mall.account.registered", payload={"user_id": user.id})
        await audit(self.db, actor_id=user.id, action="register")
        if payload.referral_code:
            from app.commerce.referral.service import ReferralService

            await ReferralService(self.db).bind(user.id, code=payload.referral_code, device=payload.device, ip=ip)
        return {"status": "accepted"}

    async def login(self, payload, *, ip: str = "", user_agent: str = ""):
        started = time.monotonic()
        try:
            return await self._authenticate(payload, ip=ip, user_agent=user_agent)
        finally:
            await asyncio.sleep(max(0, get_settings().mall_login_min_seconds - (time.monotonic() - started)))

    async def _authenticate(self, payload, *, ip, user_agent):
        counters = await attempts(self.db, identifier=payload.identifier, ip=ip)
        user = await find_identity(self.db, payload.identifier)
        hashed = user.hashed_password if user else await asyncio.to_thread(dummy_hash)
        valid = await asyncio.to_thread(verify_password, payload.password, hashed)
        if payload.verification_id:
            valid = await self._login_proof(user, payload)
        if not user or not user.is_active or not valid:
            return await failed(self.db, counters)
        try:
            await verify_factor(self.db, user.id, payload)
        except MallError:
            return await failed(self.db, counters)
        if payload.password and needs_rehash(user.hashed_password):
            user.hashed_password = await asyncio.to_thread(hash_password, payload.password)
        succeeded(counters)
        await audit(self.db, actor_id=user.id, action="login")
        return await issue_session(self.db, user, device=payload.device, ip=ip, user_agent=user_agent)

    async def _login_proof(self, user, payload):
        try:
            target, proof = await consume_proof(self.db, payload, purpose="login")
        except MallError:
            return False
        return bool(user and proof.user_id == user.id and await find_identity(self.db, target))

    async def reset_password(self, payload):
        await password_policy(payload.new_password)
        target, proof = await consume_proof(self.db, payload, purpose="password-reset")
        user = await find_identity(self.db, target)
        if user is None or user.id != proof.user_id:
            raise MallError("invalid_credentials", status=HTTPStatus.UNAUTHORIZED)
        user.hashed_password = await asyncio.to_thread(hash_password, payload.new_password)
        await revoke_all(self.db, user.id)
        await audit(self.db, actor_id=user.id, action="password_reset")
        return {"status": "accepted"}
