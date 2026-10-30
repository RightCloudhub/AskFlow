// Deterministic browser fixtures, never loaded by the application bundle.
export const FEATURES = ["core", "agent", "ticket", "handoff", "teams", "analytics", "rag",
  "knowledge", "ops", "cost", "sla", "qc", "connectors", "launch", "mall_core", "mall_account",
  "mall_admin", "mall_catalog", "mall_inventory", "mall_order", "mall_payment", "mall_wallet",
  "mall_referral", "mall_notify", "mall_support"];
export const PERMISSIONS = ["catalog:write", "inventory:write", "order:read", "order:write",
  "order:refund", "wallet:read", "wallet:adjust", "wallet:approve", "finance:reconcile",
  "settings:write", "user:manage", "rbac:write", "notify:write", "risk:review", "support:read", "audit:read"];
const GRANTS = { admin: PERMISSIONS, agent: ["order:read", "support:read"],
  catalog: ["catalog:write"], finance: ["wallet:read"], rbac: ["rbac:write"], customer: [] };
export const PRODUCT = { id: "product-af-1", title: "AskFlow 服务手册", description: "客户服务与售后流程说明",
  status: "active", version: 2, images: [], category_id: "category-1", attributes: { edition: "2026" } };
export const SKU = { id: "sku-af-1", spu_id: PRODUCT.id, code: "AF-SERVICE", title: "服务手册 · 标准版",
  sale_cents: 4900, original_cents: 5900, version: 2 };
const ROLE = { id: "role-ops", code: "operations", name: "商城运营", builtin: false, version: 1, permissions: ["catalog:write"] };
const ACCOUNT = { id: "operator-1", username: "林晓" };
const GRANT = { id: "grant-1", user_id: ACCOUNT.id, role_id: ROLE.id, username: ACCOUNT.username,
  name: ROLE.name, title: "林晓 · 商城运营" };
const LISTS = {
  "/catalog": [PRODUCT], "/catalog/skus": [SKU], "/roles": [ROLE], "/roles/users": [ACCOUNT],
  "/roles/grants": [GRANT], "/settings": [{ key: "checkout_ttl_seconds", value: 300, version: 2 }],
  "/wallet/accounts": [], "/wallet/adjustments": [], "/wallet/reversals": [],
  "/order": [], "/order/refunds/pending": [], "/notify/deliveries": [], "/support": [],
  "/notify/templates": [{ id: "template-1", event_type: "mall.order.paid", locale: "zh-CN",
    subject: "支付成功", body: "订单已收到付款。", channels: ["email"], version: 2 }],
};

export function fixtureResponse(path, identity = "admin") {
  if (path.endsWith("/features")) return { profile: "full", features: FEATURES, loaded: FEATURES,
    admin_nav: [], route_handlers: [], side_effects: [] };
  if (path.endsWith("/auth/me")) return { id: identity, username: "林晓", email: "preview@example.test",
    role: ["admin", "agent"].includes(identity) ? identity : "user", is_active: true };
  if (path === "/api/v1/mall/admin/permissions") return { permissions: GRANTS[identity] ?? [] };
  const resource = path.replace("/api/v1/admin/mall", "");
  if (resource in LISTS) return { items: LISTS[resource], next_cursor: null };
  if (["/api/v1/admin/prompts", "/api/v1/admin/tickets", "/api/v1/admin/handoffs", "/api/v1/admin/drafts"].includes(path)) return [];
  if (path === "/api/v1/mall/notify/preferences") return { items: [], next_cursor: null };
  if (path === "/api/v1/mall/account/profile") return { nickname: "林晓", locale: "zh-CN", timezone: "Asia/Shanghai", version: 1 };
  return undefined;
}
