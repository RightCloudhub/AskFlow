"""Deactivate and anonymize while retaining financial and support references."""

from sqlalchemy import update

from app.commerce.account.addresses import AddressService
from app.commerce.account.models import UserProfile, VerificationCode
from app.commerce.account.repository import identity_by_id
from app.commerce.account.sessions import revoke_all
from app.commerce.core.audit import audit
from app.commerce.core.errors import MallError
from app.commerce.core.services import enabled, service


async def close(db, user_id: str, *, actor_id: str):
    from app.services.users.retention import anonymize_support
    from app.commerce.support.privacy import anonymize

    user = await identity_by_id(db, user_id, lock=True)
    if user is None:
        raise MallError("resource_not_found", status=404)
    if enabled("order") and await service("order", db).unfinished(user_id):
        raise MallError("unfinished_orders")
    if enabled("payment") and await service("payment", db).unfinished(user_id):
        raise MallError("unfinished_payments")
    if enabled("wallet"):
        await service("wallet", db).lock()
        balance = await service("wallet", db).balance(user_id)
        if balance["available_cents"] or balance["frozen_cents"]:
            raise MallError("wallet_not_empty")
    if enabled("referral"):
        await service("referral", db).close_user(user_id)
    await revoke_all(db, user_id)
    await AddressService(db).anonymize(user_id)
    await db.execute(update(UserProfile).where(UserProfile.user_id == user_id).values(
        nickname="deleted", phone_cipher="", phone_hash=None, avatar="", region=""))
    await db.execute(update(VerificationCode).where(VerificationCode.user_id == user_id).values(
        target_cipher="", delivery_cipher="", delivery_status="cancelled"))
    if enabled("order"):
        await service("order", db).anonymize(user_id)
    await anonymize_support(db, user_id)
    await anonymize(db, user_id)
    user.is_active, user.hashed_password = False, "!disabled"
    user.username, user.email = "deleted_" + user.id, "deleted_" + user.id + "@invalid.local"
    await audit(db, actor_id=actor_id, action="account_close", resource_id=user_id)
    await db.flush()
    return {"status": "closed"}
