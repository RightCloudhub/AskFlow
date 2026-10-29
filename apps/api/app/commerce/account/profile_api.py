"""Profile settings, attachments, two-target bindings and privacy requests."""

from hashlib import sha256

from fastapi import APIRouter, UploadFile

from app.commerce.account.crypto import decrypt, digest, encrypt
from app.commerce.account.repository import find_identity, profile_for, security_for
from app.commerce.account.schemas import BindingChange, CloseAccount, ProfilePatch
from app.commerce.account.verification import consume_proof
from app.commerce.core.audit import audit
from app.commerce.core.deps import MallContext
from app.commerce.core.errors import MallError
from app.commerce.core.idempotency import execute
from app.commerce.core.repository import cas
from app.commerce.infra.runtime import infra
from app.core.config import get_settings
from app.services.users.admin import UserAdminService

router = APIRouter()


@router.get("/profile")
async def profile(ctx: MallContext):
    row, security = await profile_for(ctx.db, ctx.user.id), await security_for(ctx.db, ctx.user.id)
    return {"id": ctx.user.id, "username": ctx.user.username, "email": ctx.user.email,
            "nickname": row.nickname, "region": row.region, "locale": row.locale,
            "phone": decrypt(row.phone_cipher), "avatar": await infra().objects.url(row.avatar) if row.avatar else "",
            "email_verified": security.email_verified, "phone_verified": security.phone_verified,
            "mfa_enabled": security.mfa_enabled, "version": row.version}


@router.patch("/profile")
async def edit_profile(payload: ProfilePatch, ctx: MallContext):
    async def change():
        row = await profile_for(ctx.db, ctx.user.id)
        if row.version != payload.expected_version:
            raise MallError("version_conflict")
        values = payload.model_dump(exclude={"expected_version"})
        before = {key: getattr(row, key) for key in values}
        await cas(ctx.db, row, values=values)
        await audit(ctx.db, actor_id=ctx.user.id, action="profile_edit", detail={"before": before, "after": payload.model_dump()})
        return await profile(ctx)

    return await execute(ctx.db, scope="profile:" + ctx.user.id, key=ctx.key,
                         arguments=payload.model_dump(), action=change)


@router.post("/avatar")
async def avatar(file: UploadFile, ctx: MallContext):
    data = await file.read(get_settings().max_upload_bytes + 1)
    async def perform():
        key = await infra().objects.put(data, content_type=file.content_type or "")
        row = await profile_for(ctx.db, ctx.user.id)
        await cas(ctx.db, row, values={"avatar": key})
        await audit(ctx.db, actor_id=ctx.user.id, action="avatar_upload")
        return {"avatar": await infra().objects.url(key)}

    return await execute(ctx.db, scope="avatar:" + ctx.user.id, key=ctx.key,
        arguments={"digest": sha256(data).hexdigest(), "content_type": file.content_type}, action=perform)


@router.post("/bindings/change")
async def bindings(payload: BindingChange, ctx: MallContext):
    from app.commerce.account.mfa import require_step_up

    require_step_up(ctx, payload.step_up_token, purpose="binding_change")
    return await execute(ctx.db, scope="binding:" + ctx.user.id, key=ctx.key,
        arguments=payload.model_dump(), action=lambda: _bind(ctx, payload))


async def _bind(ctx, payload):
    old, old_proof = await consume_proof(ctx.db, payload.old, purpose="bind-old")
    new, new_proof = await consume_proof(ctx.db, payload.new, purpose="bind-new")
    row, security = await profile_for(ctx.db, ctx.user.id), await security_for(ctx.db, ctx.user.id)
    old_channel, current = _binding_origin(ctx, row=row, security=security, channel=payload.channel)
    if old != current or old_proof.user_id != ctx.user.id or old_proof.channel != old_channel or new_proof.channel != payload.channel:
        raise MallError("verification_invalid", status=401)
    other = await find_identity(ctx.db, new)
    if other and other.id != ctx.user.id:
        raise MallError("binding_unavailable")
    if payload.channel == "email":
        ctx.user.email, security.email_verified = new, True
    else:
        row.phone_cipher, row.phone_hash, security.phone_verified = encrypt(new), digest("target:" + new), True
    await audit(ctx.db, actor_id=ctx.user.id, action="binding_change", detail={"before": old, "after": new})
    return {"status": "changed"}


def _binding_origin(ctx, *, row, security, channel):
    contacts = {"email": (security.email_verified, ctx.user.email),
                "sms": (security.phone_verified, decrypt(row.phone_cipher))}
    verified, current = contacts[channel]
    if verified:
        return channel, current
    other = "sms" if channel == "email" else "email"
    verified, current = contacts[other]
    if not verified:
        raise MallError("verified_contact_required", status=403)
    return other, current


@router.get("/export")
async def export(ctx: MallContext):
    from app.commerce.order.service import OrderService
    from app.commerce.wallet.service import WalletService

    data = await UserAdminService(ctx.db).export_user_data(ctx.user.id)
    data["mall"] = {"profile": await profile(ctx), "orders": await OrderService(ctx.db).export(ctx.user.id),
                    "wallet": await WalletService(ctx.db).export(ctx.user.id)}
    await audit(ctx.db, actor_id=ctx.user.id, action="data_export")
    return data


@router.post("/close")
async def close_account(payload: CloseAccount, ctx: MallContext):
    from app.commerce.account.closure import close
    from app.commerce.account.mfa import require_step_up

    require_step_up(ctx, payload.step_up_token, purpose="account_close")
    return await close(ctx.db, ctx.user.id, actor_id=ctx.user.id)
