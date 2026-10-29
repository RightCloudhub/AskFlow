"""Minimal contact DTO for trusted notification and risk services."""

from app.commerce.account.crypto import decrypt
from app.commerce.account.repository import identity_by_id, profile_for, security_for


async def contact(db, user_id: str):
    user = await identity_by_id(db, user_id)
    if user is None:
        return None
    profile, security = await profile_for(db, user_id), await security_for(db, user_id)
    return {"email": user.email if security.email_verified else "",
            "phone": decrypt(profile.phone_cipher) if security.phone_verified else "",
            "locale": profile.locale, "phone_verified": security.phone_verified,
            "phone_hash": profile.phone_hash, "created_at": user.created_at}
