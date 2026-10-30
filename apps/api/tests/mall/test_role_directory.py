"""Role selectors share the server authorization boundary with role mutations."""

import pytest
from http import HTTPStatus
from sqlalchemy import select

from app.commerce.admin.models import AdminRole, RolePermission, UserRoleGrant
from app.models.user import User

from .helpers import headers, seed, transaction

DIRECTORY = "/api/v1/admin/mall/roles"


async def assign_permission(runtime, identity, permission):
    async def create(db):
        role = AdminRole(code="directory_" + identity["user_id"], name="角色管理员")
        db.add(role)
        await db.flush()
        db.add(RolePermission(role_id=role.id, permission_code=permission))
        db.add(UserRoleGrant(user_id=identity["user_id"], role_id=role.id,
                             assigned_by=identity["user_id"]))
        return role.id

    return await transaction(runtime, create)


@pytest.mark.asyncio
@pytest.mark.parametrize("role", ["user", "agent"])
async def test_directory_requires_explicit_rbac_permission(mall_runtime, role):
    identity = await seed(mall_runtime, role=role)
    for path in [DIRECTORY, DIRECTORY + "/users", DIRECTORY + "/grants"]:
        response = await mall_runtime.client.get(path, headers=headers(identity))
        assert response.status_code == HTTPStatus.FORBIDDEN


@pytest.mark.asyncio
async def test_rbac_operator_can_select_users_without_account_or_settings_access(mall_runtime):
    identity = await seed(mall_runtime)
    role_id = await assign_permission(mall_runtime, identity, "rbac:write")
    response = await mall_runtime.client.get(DIRECTORY + "/users", headers=headers(identity))
    assert response.status_code == HTTPStatus.OK
    account = response.json()["items"][0]
    assert set(account) == {"id", "username"}
    assert account["id"] == identity["user_id"]
    response = await mall_runtime.client.get(DIRECTORY, headers=headers(identity))
    role = next(row for row in response.json()["items"] if row["id"] == role_id)
    assert role["permissions"] == ["rbac:write"]
    for path in ["/account", "/settings", "/wallet/accounts"]:
        denied = await mall_runtime.client.get("/api/v1/admin/mall" + path, headers=headers(identity))
        assert denied.status_code == HTTPStatus.FORBIDDEN


@pytest.mark.asyncio
async def test_grant_selector_and_revocation_refresh_permissions(mall_runtime):
    admin = await seed(mall_runtime, role="admin")
    customer = await seed(mall_runtime)
    role_id = await assign_permission(mall_runtime, customer, "catalog:write")
    response = await mall_runtime.client.get(DIRECTORY + "/grants", headers=headers(admin))
    assert response.status_code == HTTPStatus.OK
    grant = next(row for row in response.json()["items"] if row["user_id"] == customer["user_id"])
    assert grant["role_id"] == role_id
    assert grant["username"] in grant["title"]
    revoked = await mall_runtime.client.delete(
        DIRECTORY + f"/grants/{customer['user_id']}/{role_id}", headers=headers(admin),
    )
    assert revoked.status_code == HTTPStatus.OK
    permissions = await mall_runtime.client.get("/api/v1/mall/admin/permissions", headers=headers(customer))
    assert "catalog:write" not in permissions.json()["permissions"]
    grants = await mall_runtime.client.get(DIRECTORY + "/grants", headers=headers(admin))
    assert not any(row["id"] == grant["id"] for row in grants.json()["items"])


@pytest.mark.asyncio
async def test_account_selector_excludes_inactive_and_pages_without_duplicates(mall_runtime, monkeypatch):
    from app.commerce.admin import role_directory

    monkeypatch.setattr(role_directory, "PAGE_SIZE", 1)
    admin = await seed(mall_runtime, role="admin")
    customer = await seed(mall_runtime)
    inactive = await seed(mall_runtime)
    async with mall_runtime.sessions() as db:
        user = await db.scalar(select(User).where(User.id == inactive["user_id"]))
        user.is_active = False
        await db.commit()
    first = await mall_runtime.client.get(DIRECTORY + "/users", headers=headers(admin))
    cursor = first.json()["next_cursor"]
    assert cursor is not None
    second = await mall_runtime.client.get(DIRECTORY + "/users", params={"cursor": cursor}, headers=headers(admin))
    ids = [row["id"] for row in first.json()["items"] + second.json()["items"]]
    assert sorted(ids) == sorted([admin["user_id"], customer["user_id"]])
    assert second.json()["next_cursor"] is None
