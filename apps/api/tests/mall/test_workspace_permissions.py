"""Workspace URLs and role grants cannot bypass API authorization."""

from http import HTTPStatus

import pytest
from sqlalchemy import select

from app.commerce.admin.models import AdminRole, RolePermission, UserRoleGrant

from .helpers import headers, seed, transaction

ADMIN = "/api/v1/admin"


async def grant_permission(runtime, identity, permission):
    async def create(db):
        role = AdminRole(code="workspace_" + identity["user_id"], name="业务协作")
        db.add(role)
        await db.flush()
        db.add(RolePermission(role_id=role.id, permission_code=permission))
        db.add(UserRoleGrant(user_id=identity["user_id"], role_id=role.id,
                             assigned_by=identity["user_id"]))
        return role.id

    return await transaction(runtime, create)


@pytest.mark.asyncio
@pytest.mark.parametrize("role", ["user", "agent"])
async def test_system_workspace_requires_administrator(mall_runtime, role):
    identity = await seed(mall_runtime, role=role)
    for endpoint in ["/infra", "/users", "/audit-logs", "/mall/settings", "/mall/roles"]:
        response = await mall_runtime.client.get(ADMIN + endpoint, headers=headers(identity))
        assert response.status_code == HTTPStatus.FORBIDDEN, endpoint


@pytest.mark.asyncio
async def test_catalog_operator_cannot_read_finance_or_change_roles(mall_runtime):
    identity = await seed(mall_runtime)
    await grant_permission(mall_runtime, identity, "catalog:write")
    allowed = await mall_runtime.client.get(ADMIN + "/mall/catalog", headers=headers(identity))
    assert allowed.status_code == HTTPStatus.OK
    for endpoint in ["/mall/wallet/accounts", "/mall/order", "/mall/account", "/mall/notify/templates"]:
        response = await mall_runtime.client.get(ADMIN + endpoint, headers=headers(identity))
        assert response.status_code == HTTPStatus.FORBIDDEN, endpoint
    response = await mall_runtime.client.post(ADMIN + "/mall/roles/grant", headers=headers(identity),
        json={"user_id": identity["user_id"], "role": "superadmin"})
    assert response.status_code == HTTPStatus.FORBIDDEN


@pytest.mark.asyncio
async def test_revocation_invalidates_existing_access_token(mall_runtime):
    identity = await seed(mall_runtime)
    role_id = await grant_permission(mall_runtime, identity, "catalog:write")
    credential = headers(identity)
    path = ADMIN + "/mall/catalog"
    assert (await mall_runtime.client.get(path, headers=credential)).status_code == HTTPStatus.OK
    async with mall_runtime.sessions() as db:
        grant = await db.scalar(select(UserRoleGrant).where(UserRoleGrant.role_id == role_id))
        await db.delete(grant)
        await db.commit()
    assert (await mall_runtime.client.get(path, headers=credential)).status_code == HTTPStatus.FORBIDDEN
