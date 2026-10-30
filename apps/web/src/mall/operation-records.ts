import type { Operation } from "./admin-operations";
import type { Row } from "./shared";
import { MINOR_UNITS } from "./money-values.ts";

export type OperationResource = { path: string; field?: string; valueKey?: string; label: string;
  permission: string; excludeBuiltin?: boolean; boundFields?: string[] };
const RESOURCES: Array<{ match: string; resource: OperationResource }> = [
  { match: "/catalog/products/:id", resource: { path: "/catalog", field: "id", label: "商品", permission: "catalog:write" } },
  { match: "/catalog/skus/:id", resource: { path: "/catalog/skus", field: "id", label: "商品规格", permission: "catalog:write" } },
  { match: "/account/:id", resource: { path: "/account", field: "id", label: "用户", permission: "user:manage" } },
  { match: "/account/mfa-resets/:id", resource: { path: "/account/mfa-resets", field: "id", label: "重置申请", permission: "user:manage" } },
  { match: "/inventory/:id", resource: { path: "/inventory", field: "id", valueKey: "sku_id", label: "库存规格", permission: "inventory:write" } },
  { match: "/order/:id", resource: { path: "/order", field: "id", label: "订单", permission: "order:read" } },
  { match: "/order/refunds/:id", resource: { path: "/order/refunds/pending", field: "id", label: "退款申请", permission: "order:refund" } },
  { match: "/wallet/adjustments/:id", resource: { path: "/wallet/adjustments", field: "id", label: "调账申请", permission: "wallet:read" } },
  { match: "/wallet/reversals/:id", resource: { path: "/wallet/reversals", field: "id", label: "冲正申请", permission: "wallet:read" } },
  { match: "/referral/:id", resource: { path: "/referral", field: "id", label: "风控事件", permission: "risk:review" } },
  { match: "/settings/:id", resource: { path: "/settings", field: "id", valueKey: "key", label: "配置项", permission: "settings:write" } },
  { match: "/roles/:id", resource: { path: "/roles", field: "id", label: "自定义角色", permission: "rbac:write", excludeBuiltin: true } },
  { match: "/roles/grants/", resource: { path: "/roles/grants", label: "角色授权", permission: "rbac:write", boundFields: ["user_id", "role_id"] } },
];

export function operationResource(operation: Operation, permissions: readonly string[]) {
  let resource = RESOURCES.find((item) => operation.path.startsWith(item.match))?.resource;
  if (operation.path === "/catalog/skus") resource = { path: "/catalog", field: "spu_id", label: "所属商品", permission: "catalog:write" };
  if (operation.path === "/inventory/flash-sales") resource = { path: "/catalog/skus", field: "sku_id", label: "活动规格", permission: "catalog:write" };
  if (operation.path === "/roles/grant") resource = { path: "/roles/users", field: "user_id", label: "授权账号", permission: "rbac:write" };
  if (operation.path === "/notify/templates" && operation.editExisting) resource = {
    path: "/notify/templates", label: "通知模板", permission: "notify:write", boundFields: ["event_type", "locale"],
  };
  return resource && permissions.includes(resource.permission) ? resource : undefined;
}

export function recordLabel(row: Row) {
  const identity = row.title ?? row.username ?? row.name ?? row.subject ?? row.key ?? row.sku_id ?? row.id;
  return String(identity ?? "") + (row.code ? ` · ${row.code}` : "");
}

/** Version comes from the selected server record, never a guessed default. */
export function operationInitial(options: { operation: Operation; resource?: OperationResource; row?: Row }) {
  const { operation } = options;
  const defaults: Row = { locale: "zh-CN", channels: [], permissions: [] };
  const initial: Row = Object.fromEntries(operation.fields.filter((field) => field.name in defaults)
    .map((field) => [field.name, defaults[field.name]]));
  if (operation.path === "/notify/templates" && !operation.editExisting) initial.expected_version = 0;
  return { ...initial, ...selectedInitial(options) };
}

function selectedInitial({ operation, resource, row }: { operation: Operation; resource?: OperationResource; row?: Row }) {
  if (!resource || !row) return {};
  const initial = recordValues(operation, row);
  if (resource.field) initial[resource.field] = row[resource.valueKey ?? "id"];
  if (row.version !== undefined && operation.fields.some((field) => field.name === "expected_version")) initial.expected_version = row.version;
  if (row.is_active !== undefined && operation.fields.some((field) => field.name === "active")) initial.active = row.is_active;
  if (Array.isArray(initial.images)) initial.images = initial.images.join(",");
  return initial;
}

function recordValues(operation: Operation, row: Row) {
  return Object.fromEntries(operation.fields.filter((field) => row[field.name] !== undefined).map((field) => {
    const value = row[field.name];
    return [field.name, field.kind === "money" && typeof value === "number" ? value / MINOR_UNITS : value];
  }));
}
