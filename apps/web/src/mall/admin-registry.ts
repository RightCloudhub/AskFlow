import type { AdminNavItem, AdminRouteDef } from "../plugins/types";

export const MALL_ADMIN = [
  { module: "dashboard", plugin: "mall_admin", label: "商城概览", permission: "order:read" },
  { module: "account", label: "商城用户", permission: "user:manage" },
  { module: "catalog", label: "商城商品", permission: "catalog:write" },
  { module: "inventory", label: "商城库存", permission: "inventory:write" },
  { module: "order", label: "商城订单", permission: "order:read" },
  { module: "payment", label: "商城支付", permission: "finance:reconcile" },
  { module: "wallet", label: "商城财务", permission: "wallet:read" },
  { module: "referral", label: "邀请风控", permission: "risk:review" },
  { module: "notify", label: "商城通知", permission: "notify:write" },
  { module: "support", label: "商城客服", permission: "support:read" },
  { module: "settings", plugin: "mall_admin", label: "商城配置与权限", permission: "settings:write" },
];
const NAV_ORDER = 110;

export const MALL_NAV: AdminNavItem[] = MALL_ADMIN.map((item, index) => ({
  pluginId: item.plugin ?? `mall_${item.module}`, to: `/admin/mall/${item.module}`,
  label: item.label, group: "system", order: NAV_ORDER + index,
}));
MALL_NAV.push({ pluginId: "mall_core", to: "/admin/infra", label: "基础设施", order: NAV_ORDER, group: "system" });

export const MALL_ROUTES: AdminRouteDef[] = [
  ...MALL_ADMIN.map((item) => ({ pluginId: item.plugin ?? `mall_${item.module}`,
    path: `mall/${item.module}`, page: "mall-admin" })),
  { pluginId: "mall_core", path: "infra", page: "mall-infra" },
];
