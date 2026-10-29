"""Permission checks are enforced before any domain mutation."""

from fastapi import Depends
from sqlalchemy import select

from app.commerce.admin.models import AdminRole, RolePermission, UserRoleGrant
from app.commerce.core.audit import audit
from app.commerce.core.deps import MallContext
from app.commerce.core.errors import MallError
from app.commerce.core.repository import insert_once

PERMISSIONS = frozenset({
    "catalog:write", "inventory:write", "order:read", "order:write", "order:refund",
    "wallet:read", "wallet:adjust", "wallet:approve", "finance:reconcile",
    "settings:write", "user:manage", "rbac:write", "notify:write", "risk:review",
    "support:read", "audit:read",
})
ROLES = {
    "superadmin": PERMISSIONS,
    "operations": {"catalog:write", "inventory:write", "order:read", "order:write",
                   "order:refund", "notify:write", "risk:review"},
    "support": {"order:read", "support:read"},
    "finance": {"wallet:read", "wallet:adjust", "wallet:approve", "finance:reconcile"},
    "auditor": {"order:read", "wallet:read", "support:read", "audit:read"},
}


async def permissions_for(db, user):
    if user.role == "admin":
        return PERMISSIONS
    values = await db.scalars(select(RolePermission.permission_code).join(
        UserRoleGrant, UserRoleGrant.role_id == RolePermission.role_id
    ).where(UserRoleGrant.user_id == user.id))
    baseline = ROLES["support"] if user.role == "agent" else set()
    return frozenset(values) | baseline


async def recipients(db, permission: str):
    from app.models.user import User

    granted = select(UserRoleGrant.user_id).join(RolePermission,
        RolePermission.role_id == UserRoleGrant.role_id).where(RolePermission.permission_code == permission)
    return list(await db.scalars(select(User.id).where(User.is_active,
        (User.role == "admin") | User.id.in_(granted))))


async def check(ctx, permission: str):
    if permission in await permissions_for(ctx.db, ctx.user):
        return ctx
    await audit(ctx.db, actor_id=ctx.user.id, action="permission_denied",
                detail={"permission": permission})
    raise MallError("permission_denied", status=403, persist=True)


def require(permission: str):
    async def dependency(ctx: MallContext):
        return await check(ctx, permission)

    return Depends(dependency)


async def seed_roles(db):
    from app.commerce.admin.models import AdminPermission

    for code in sorted(PERMISSIONS):
        await insert_once(db, AdminPermission, values={"code": code}, unique=["code"])
    for code, permissions in ROLES.items():
        await insert_once(db, AdminRole, values={"code": code, "name": code, "builtin": True},
                          unique=["code"])
        role = await db.scalar(select(AdminRole).where(AdminRole.code == code))
        for permission in sorted(permissions):
            await insert_once(db, RolePermission, values={"role_id": role.id,
                "permission_code": permission}, unique=["role_id", "permission_code"])
