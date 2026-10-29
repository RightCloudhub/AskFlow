"""Actual before/after rows survive bulk updates, role inserts and deletions."""

from sqlalchemy import select

from app.commerce.admin.models import UserRoleGrant
from app.models.audit import AuditLog

from .account_helpers import register_customer
from .helpers import headers, seed


async def audit_for(runtime, action):
    async with runtime.sessions() as db:
        row = await db.scalar(select(AuditLog).where(AuditLog.action == action).order_by(AuditLog.created_at.desc()))
        assert row is not None
        return row.detail["changes"]


async def test_role_grant_and_revoke_capture_actual_membership(mall_runtime):
    administrator = await seed(mall_runtime, role="admin")
    customer = await register_customer(mall_runtime)
    response = await mall_runtime.client.post("/api/v1/admin/mall/roles/grant",
        headers=headers(administrator), json={"user_id": customer["user_id"], "role": "finance"})
    assert response.status_code == 200, response.text
    changes = await audit_for(mall_runtime, "mall.rbac.grant")
    assert_grant_created(changes, customer["user_id"])
    async with mall_runtime.sessions() as db:
        grant = await db.scalar(select(UserRoleGrant).where(UserRoleGrant.user_id == customer["user_id"]))
        role_id = grant.role_id
    response = await mall_runtime.client.delete(
        f"/api/v1/admin/mall/roles/grants/{customer['user_id']}/{role_id}", headers=headers(administrator))
    assert response.status_code == 200, response.text
    changes = await audit_for(mall_runtime, "mall.role.revoke")
    grants = [row for row in changes if row["table"] == "user_roles"]
    assert grants[0]["before"]["role_id"] == role_id
    assert grants[0]["after"] is None


def assert_grant_created(changes, user_id):
    grants = [row for row in changes if row["table"] == "user_roles"]
    assert len(grants) == 1
    assert grants[0]["before"] is None
    assert grants[0]["after"]["user_id"] == user_id


async def test_inventory_bulk_update_has_before_after(mall_runtime):
    administrator = await seed(mall_runtime, role="admin", stock=7)
    response = await mall_runtime.client.post(
        "/api/v1/admin/mall/inventory/" + administrator["sku_id"] + "/replenish",
        headers=headers(administrator), json={"quantity": 3, "expected_version": 0})
    assert response.status_code == 200, response.text
    changes = await audit_for(mall_runtime, "mall.inventory.replenish:" + administrator["sku_id"])
    stock = next(row for row in changes if row["table"] == "inventory")
    assert stock["before"]["available"] == 7
    assert stock["after"]["available"] == 10
    assert stock["after"]["version"] == stock["before"]["version"] + 1
