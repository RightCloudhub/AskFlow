import assert from "node:assert/strict";
import test from "node:test";
import { accessibleNavigation, canAccessAdmin, currentWorkspace, workspacePath } from "../src/admin/access-policy.ts";
import { MALL_NAV } from "../src/mall/admin-registry.ts";
import { loginReturnPath } from "../src/pages/auth/return-path.ts";

test("customer, agent and administrator get distinct service access", () => {
  for (const path of ["handoffs", "tickets", "users", "plugins", ""]) {
    assert.equal(canAccessAdmin(path, { role: "user", permissions: [] }), false);
    assert.equal(canAccessAdmin(path, { permissions: [] }), false);
    assert.equal(canAccessAdmin(path, { role: "admin", permissions: [] }), true);
  }
  assert.equal(canAccessAdmin("handoffs", { role: "agent", permissions: [] }), true);
  assert.equal(canAccessAdmin("users", { role: "agent", permissions: [] }), false);
  assert.equal(canAccessAdmin("teams", { role: "agent", permissions: [] }), false);
  assert.equal(canAccessAdmin("infra", { role: "agent", permissions: [] }), false);
});

test("revoked permissions remove the corresponding workspace destinations", () => {
  const features = new Set(["mall_catalog", "mall_admin"]);
  const before = accessibleNavigation({ items: MALL_NAV, features,
    identity: { role: "user", permissions: ["catalog:write", "rbac:write"] } });
  const after = accessibleNavigation({ items: MALL_NAV, features,
    identity: { role: "user", permissions: ["rbac:write"] } });
  assert.ok(before.some((item) => item.to.startsWith("/admin/commerce/")));
  assert.deepEqual(after.map((item) => item.to), ["/admin/system/mall/roles"]);
});

test("granted business permissions do not grant unrelated system or finance access", () => {
  const identity = { role: "user", permissions: ["catalog:write"] };
  assert.equal(canAccessAdmin("mall/catalog", identity), true);
  for (const path of ["mall/wallet", "mall/roles", "mall/settings", "infra", "users"]) {
    assert.equal(canAccessAdmin(path, identity), false);
  }
  assert.equal(canAccessAdmin("mall/roles", { role: "user", permissions: ["rbac:write"] }), true);
  assert.equal(canAccessAdmin("mall/settings", { role: "user", permissions: ["rbac:write"] }), false);
});

test("navigation requires both the enabled feature and a server permission", () => {
  const identity = { role: "user", permissions: ["catalog:write", "wallet:read"] };
  const items = accessibleNavigation({ items: MALL_NAV, features: new Set(["mall_catalog"]), identity });
  assert.deepEqual(items.map((item) => item.to), ["/admin/commerce/mall/catalog"]);
  assert.deepEqual(accessibleNavigation({ items: MALL_NAV, features: new Set(["mall_catalog"]),
    identity: { role: "user", permissions: [] } }), []);
});

test("legacy destinations map to independent workspaces without ambiguous prefixes", () => {
  assert.equal(workspacePath("handoffs"), "/admin/service/handoffs");
  assert.equal(workspacePath("mall/support"), "/admin/service/mall/support");
  assert.equal(workspacePath("mall/order"), "/admin/commerce/mall/order");
  assert.equal(workspacePath("mall/roles"), "/admin/system/mall/roles");
  assert.equal(workspacePath(""), "/admin/service/overview");
  assert.equal(currentWorkspace("/admin/systematic"), undefined);
  assert.equal(currentWorkspace("/admin/system/mall/roles")?.id, "system");
});

test("action-only roles see their business workspace without gaining read permissions", () => {
  const refund = { role: "user", permissions: ["order:refund"] };
  assert.equal(canAccessAdmin("mall/order", refund), true);
  assert.equal(canAccessAdmin("mall/dashboard", refund), false);
  assert.equal(canAccessAdmin("mall/wallet", refund), false);
  assert.equal(canAccessAdmin("mall/wallet", { role: "user", permissions: ["wallet:adjust"] }), true);
});

test("login resumes local workspace links and refuses redirect escapes", () => {
  const path = "/admin/system/mall/roles?source=invite#permissions";
  assert.equal(loginReturnPath(path, "/shop"), path);
  for (const value of [null, "https://outside.test", "//outside.test", "/\\outside.test", "/login", "/admin/../../login"]) {
    assert.equal(loginReturnPath(value, "/shop"), "/shop");
  }
});
