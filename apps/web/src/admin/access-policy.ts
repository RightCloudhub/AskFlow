import type { AdminNavItem, AdminRouteDef } from "../plugins/types";
import { mallModuleAllowed } from "../mall/menu.ts";

export type AdminWorkspace = "service" | "commerce" | "system";
export type AccessIdentity = { role?: string; permissions: readonly string[] };
export const ADMIN_WORKSPACES = [
  { id: "service", title: "客服运营", description: "接待客户、跟进工单，维护服务知识。" },
  { id: "commerce", title: "商城管理", description: "管理商品、库存、订单与财务。" },
  { id: "system", title: "系统管理", description: "管理账号权限、配置与系统运行。" },
] as const;
const STAFF_PAGES = new Set(["handoffs", "tickets"]);
const SYSTEM_PAGES = new Set(["users", "audit", "connectors", "plugins", "launch-cards",
  "intents", "prompts", "agent-runs", "costs", "infra"]);
const SYSTEM_MODULES = new Set(["account", "settings", "roles"]);

export function workspaceFor(path: string): AdminWorkspace {
  if (path.startsWith("mall/")) {
    const module = path.slice("mall/".length);
    if (module === "support") return "service";
    return SYSTEM_MODULES.has(module) ? "system" : "commerce";
  }
  return SYSTEM_PAGES.has(path) ? "system" : "service";
}

export function workspacePath(path: string) {
  return `/admin/${workspaceFor(path)}/${path || "overview"}`;
}

/** Mirror server permissions; feature discovery never grants authorization. */
export function canAccessAdmin(path: string, identity: AccessIdentity) {
  if (path.startsWith("mall/")) {
    return mallModuleAllowed(path.slice("mall/".length), identity.permissions);
  }
  if (!identity.role) return false;
  if (identity.role === "admin") return true;
  return identity.role === "agent" && STAFF_PAGES.has(path);
}

export function accessibleNavigation(options: {
  items: AdminNavItem[]; features: Set<string>; identity: AccessIdentity;
}) {
  return options.items.filter((item) => options.features.has(item.pluginId)
    && canAccessAdmin(item.to.replace(/^\/admin\/?/, ""), options.identity))
    .map((item) => ({ ...item, to: workspacePath(item.to.replace(/^\/admin\/?/, "")) }));
}

export function canonicalRoute(route: AdminRouteDef) {
  return workspacePath(route.path).replace(/^\/admin\//, "");
}

export function currentWorkspace(pathname: string) {
  return ADMIN_WORKSPACES.find((workspace) => pathname === `/admin/${workspace.id}`
    || pathname.startsWith(`/admin/${workspace.id}/`));
}
