"""Account-owned identity interface for other commerce domains."""

from app.commerce.account.repository import identity_by_id, profile_for, security_for


async def active_identity(db, user_id: str, *, lock: bool = False):
    user = await identity_by_id(db, user_id, lock=lock)
    return {"id": user.id, "role": user.role} if user else None


async def initialize_extensions(db, user_id: str):
    await profile_for(db, user_id)
    await security_for(db, user_id)
