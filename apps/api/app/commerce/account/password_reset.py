"""Uniform reset challenges use verified contact channels without fake email addresses."""

import asyncio
import time

from app.commerce.account.contacts import contact
from app.commerce.account.crypto import digest
from app.commerce.account.repository import find_identity
from app.commerce.account.schemas import VerificationSend
from app.commerce.account.verification import create_challenge
from app.commerce.core.errors import MallError
from app.core.config import get_settings
from app.models.mixins import new_uuid


async def forgot(db, identifier: str):
    started = time.monotonic()
    try:
        return await _challenge(db, identifier)
    finally:
        remaining = get_settings().mall_login_min_seconds - (time.monotonic() - started)
        await asyncio.sleep(max(0, remaining))


async def _challenge(db, identifier: str):
    user = await find_identity(db, identifier)
    recipient = await contact(db, user.id) if user else None
    target = digest("reset-unknown:" + identifier.strip().lower())
    channel, deliver = "email", False
    if recipient:
        channel = "email" if recipient["email"] else "sms"
        target = recipient["email"] or recipient["phone"] or target
        deliver = bool(recipient["email"] or recipient["phone"])
    payload = VerificationSend(target=target, channel=channel, purpose="password-reset")
    try:
        return await create_challenge(db, payload, target=target,
                                      user_id=user.id if user else None, deliver=deliver)
    except MallError as exc:
        if exc.code != "verification_rate_limited":
            raise
        # A cooldown must not reveal whether this identifier owns a delivery target.
        return {"status": "accepted", "challenge_id": new_uuid()}
