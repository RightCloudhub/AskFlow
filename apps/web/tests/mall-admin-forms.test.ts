import assert from "node:assert/strict";
import test from "node:test";
import { quietHoursError, quietLabel } from "../src/mall/notification-options.ts";
import { OPERATIONS } from "../src/mall/admin-operations.ts";
import { operationInitial, operationResource } from "../src/mall/operation-records.ts";
import { operationPayload } from "../src/mall/operation-payload.ts";
import { submissionValues } from "../src/mall/money-values.ts";
import { operationFields } from "../src/mall/operation-fields.ts";

test("inventory picker submits SKU identity and exact server version", () => {
  const operation = OPERATIONS.inventory[0];
  const resource = operationResource(operation, ["inventory:write"]);
  const values = operationInitial({ operation, resource, row: { id: "inventory-1", sku_id: "sku/one", version: 0 } });
  const command = operationPayload({ operation, values: { ...values, quantity: 5, unrelated: "ignored" }, token: "" });
  assert.equal(command.path, "/api/v1/admin/mall/inventory/sku%2Fone/replenish");
  assert.deepEqual(command.body, { expected_version: 0, quantity: 5 });
});

test("price edits display major units and submit integer minor units once", () => {
  const operation = OPERATIONS.catalog.find((item) => item.title === "更新价格")!;
  const resource = operationResource(operation, ["catalog:write"]);
  const initial = operationInitial({ operation, resource, row: { id: "sku", version: 3, sale_cents: 1234, original_cents: 2000 } });
  assert.equal(initial.sale_cents, 12.34);
  const command = operationPayload({ operation, values: submissionValues(initial, operation.fields), token: "" });
  assert.deepEqual(command.body, { expected_version: 3, sale_cents: 1234, original_cents: 2000 });
});

test("role editing preserves existing permission selections and supports removing all", () => {
  const operation = OPERATIONS.roles.find((item) => item.title === "角色权限")!;
  const resource = operationResource(operation, ["rbac:write"]);
  const initial = operationInitial({ operation, resource, row: { id: "role", version: 4, permissions: ["order:read"] } });
  assert.deepEqual(initial.permissions, ["order:read"]);
  const command = operationPayload({ operation, values: { ...initial, permissions: [] }, token: "" });
  assert.deepEqual(command.body, { expected_version: 4, permissions: [] });
});

test("account state commands never gain unrelated initial defaults or a version field", () => {
  const operation = OPERATIONS.account[0];
  const resource = operationResource(operation, ["user:manage"]);
  const initial = operationInitial({ operation, resource, row: { id: "account", is_active: false, version: 1 } });
  assert.deepEqual(initial, { id: "account", active: false });
  assert.equal(operationResource(operation, ["rbac:write"]), undefined);
});

test("notification channel selections remain arrays in the server payload", () => {
  const operation = OPERATIONS.notify[0];
  const values = { event_type: "mall.order.paid", locale: "zh-CN", subject: "支付成功", body: "订单已支付", channels: ["email", "sms"], expected_version: 0 };
  assert.deepEqual(operationPayload({ operation, values, token: "" }).body, values);
});

test("editing product copy preserves category and attributes from the selected record", () => {
  const operation = OPERATIONS.catalog.find((item) => item.title === "修改商品")!;
  const command = operationPayload({ operation, token: "", values: { id: "product", expected_version: 2, title: "更新名称" },
    record: { category_id: "category", attributes: { material: "cotton" } } });
  assert.equal(command.body.category_id, "category");
  assert.deepEqual(command.body.attributes, { material: "cotton" });
});

test("SKU details and prices occupy separate steps after choosing the parent product", () => {
  const operation = OPERATIONS.catalog.find((item) => item.title === "新增规格")!;
  const resource = operationResource(operation, ["catalog:write"]);
  const fields = operationFields({ operation, resource, row: { id: "product" }, roles: [] });
  assert.equal(fields.find((field) => field.name === "spu_id")?.hidden, true);
  assert.equal(fields.find((field) => field.name === "code")?.step, "规格信息");
  assert.equal(fields.find((field) => field.name === "sale_cents")?.step, "价格设置");
});

test("notification editors bind event, language and current version to the selected template", () => {
  const operation = OPERATIONS.notify.find((item) => item.editExisting)!;
  const resource = operationResource(operation, ["notify:write"]);
  const row = { id: "template", event_type: "mall.order.paid", locale: "en-US", version: 7,
    subject: "Payment received", body: "Your order is paid", channels: ["email"] };
  const initial = operationInitial({ operation, resource, row });
  const fields = operationFields({ operation, resource, row, roles: [] });
  assert.equal(initial.expected_version, 7);
  assert.equal(initial.locale, "en-US");
  for (const name of ["event_type", "locale", "expected_version"]) {
    assert.equal(fields.find((field) => field.name === name)?.hidden, true);
  }
  assert.deepEqual(operationPayload({ operation, values: initial, token: "" }).body,
    { event_type: row.event_type, locale: row.locale, subject: row.subject, body: row.body,
      channels: row.channels, expected_version: 7 });
  assert.equal(operationInitial({ operation: OPERATIONS.notify[0] }).expected_version, 0);
});

test("quiet hours accept overnight ranges and reject incomplete or empty ranges", () => {
  assert.equal(quietHoursError(22, 8), undefined);
  assert.equal(quietHoursError(-1, -1), undefined);
  assert.ok(quietHoursError(-1, 8));
  assert.ok(quietHoursError(22, -1));
  assert.ok(quietHoursError(8, 8));
  assert.equal(quietLabel({ quiet_start: 22, quiet_end: 8, timezone: "Asia/Shanghai" }),
    "22:00–08:00 静默 · Asia/Shanghai");
});
