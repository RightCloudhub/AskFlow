import type { AdminNavItem, AdminRouteDef, FeatureId } from "./types";

/** Static catalog — filtered by enabled features at runtime. */
export const ADMIN_NAV: AdminNavItem[] = [
  { pluginId: "analytics", to: "/admin", label: "看板", order: 10 },
  { pluginId: "qc", to: "/admin/qc", label: "质检", order: 15 },
  { pluginId: "rag", to: "/admin/documents", label: "文档", order: 20 },
  { pluginId: "ops", to: "/admin/intents", label: "意图", order: 21 },
  { pluginId: "ops", to: "/admin/prompts", label: "Prompt", order: 22 },
  { pluginId: "knowledge", to: "/admin/gaps", label: "缺口", order: 30 },
  { pluginId: "knowledge", to: "/admin/drafts", label: "草稿", order: 31 },
  { pluginId: "handoff", to: "/admin/handoffs", label: "接管", order: 40 },
  { pluginId: "ticket", to: "/admin/tickets", label: "工单", order: 50 },
  { pluginId: "core", to: "/admin/audit", label: "审计", order: 90 },
  { pluginId: "core", to: "/admin/users", label: "用户", order: 91 },
  { pluginId: "connectors", to: "/admin/connectors", label: "连接器", order: 92 },
  { pluginId: "cost", to: "/admin/costs", label: "成本", order: 93 },
  { pluginId: "launch", to: "/admin/launch-cards", label: "Launch", order: 94 },
  { pluginId: "teams", to: "/admin/teams", label: "技能组", order: 55 },
  { pluginId: "sla", to: "/admin/sla", label: "SLA", order: 56 },
  { pluginId: "agent", to: "/admin/agent-runs", label: "Agent Runs", order: 95 },
];

export const ADMIN_ROUTES: AdminRouteDef[] = [
  { path: "", pluginId: "analytics", page: "dashboard" },
  { path: "qc", pluginId: "qc", page: "qc" },
  { path: "documents", pluginId: "rag", page: "documents" },
  { path: "intents", pluginId: "ops", page: "intents" },
  { path: "prompts", pluginId: "ops", page: "prompts" },
  { path: "gaps", pluginId: "knowledge", page: "gaps" },
  { path: "drafts", pluginId: "knowledge", page: "drafts" },
  { path: "handoffs", pluginId: "handoff", page: "handoffs" },
  { path: "tickets", pluginId: "ticket", page: "tickets" },
  { path: "teams", pluginId: "teams", page: "teams" },
  { path: "sla", pluginId: "sla", page: "sla" },
  { path: "audit", pluginId: "core", page: "audit" },
  { path: "users", pluginId: "core", page: "users" },
  { path: "connectors", pluginId: "connectors", page: "connectors" },
  { path: "costs", pluginId: "cost", page: "costs" },
  { path: "launch-cards", pluginId: "launch", page: "launch-cards" },
  { path: "agent-runs", pluginId: "agent", page: "agent-runs" },
];

/** Fail-closed baseline when discovery fails or list is empty (AC4). */
export const CORE_FEATURES: FeatureId[] = ["core"];

/** Full catalog (env override / known profiles only — not used on API failure). */
export const DEFAULT_FEATURES: FeatureId[] = [
  "core",
  "rag",
  "agent",
  "tools",
  "ticket",
  "handoff",
  "knowledge",
  "ops",
  "cost",
  "sla",
  "notify",
  "sso",
  "teams",
  "connectors",
  "launch",
  "analytics",
  "mcp",
  "widget",
  "feishu",
  "qc",
];

export function filterNav(
  features: Set<string>,
  items: AdminNavItem[] = ADMIN_NAV
): AdminNavItem[] {
  return items
    .filter((i) => features.has(i.pluginId))
    .sort((a, b) => a.order - b.order || a.to.localeCompare(b.to));
}

export function filterRoutes(
  features: Set<string>,
  routes: AdminRouteDef[] = ADMIN_ROUTES
): AdminRouteDef[] {
  return routes.filter((r) => features.has(r.pluginId));
}

export function parseEnvFeatures(): Set<string> | null {
  const raw = import.meta.env.VITE_ASKFLOW_FEATURES as string | undefined;
  if (!raw || !raw.trim()) return null;
  return new Set(
    raw
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean)
  );
}
