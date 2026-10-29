"""Identity lookup is confined to the account boundary."""

from sqlalchemy import func, or_, select

from app.commerce.account.crypto import digest
from app.commerce.account.models import UserProfile, UserSecurity
from app.commerce.core.repository import insert_once
from app.models.user import User


async def find_identity(db, identifier: str):
    normalized = identifier.strip().lower()
    return await db.scalar(select(User).outerjoin(UserProfile, UserProfile.user_id == User.id).where(
        or_(func.lower(User.username) == normalized, func.lower(User.email) == normalized,
            UserProfile.phone_hash == digest("target:" + normalized))))


async def security_for(db, user_id: str):
    await insert_once(db, UserSecurity, values={"user_id": user_id}, unique=["user_id"])
    return await db.scalar(select(UserSecurity).where(UserSecurity.user_id == user_id)
                           .execution_options(populate_existing=True))


async def profile_for(db, user_id: str):
    await insert_once(db, UserProfile, values={"user_id": user_id}, unique=["user_id"])
    return await db.scalar(select(UserProfile).where(UserProfile.user_id == user_id)
                           .execution_options(populate_existing=True))


async def identity_by_id(db, user_id: str, *, lock: bool = False):
    statement = select(User).where(User.id == user_id, User.is_active)
    if lock:
        statement = statement.with_for_update(key_share=True)
    return await db.scalar(statement.execution_options(populate_existing=True))
