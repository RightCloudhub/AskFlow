import assert from "node:assert/strict";
import test from "node:test";
import { mallMenuAllowed } from "../src/mall/menu.ts";
import { MALL_ADMIN } from "../src/mall/admin-registry.ts";

test("every mall menu requires its own permission", () => {
  for (const entry of MALL_ADMIN) {
    const path = `/admin/mall/${entry.module}`;
    assert.equal(mallMenuAllowed(path, []), false);
    assert.equal(mallMenuAllowed(path, [entry.permission]), true);
  }
});

test("catalog permission cannot expose financial administration", () => {
  assert.equal(mallMenuAllowed("/admin/mall/wallet", ["catalog:write"]), false);
  assert.equal(mallMenuAllowed("/admin/infra", []), false);
});

test("legacy navigation keeps its existing behavior", () => {
  assert.equal(mallMenuAllowed("/admin/tickets", []), true);
  assert.equal(mallMenuAllowed("/admin/plugins", []), true);
});
