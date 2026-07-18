import type { AdminNavItem, AdminRouteDef, FeatureId, NavGroupId } from "./types";

export type NavGroupMeta = {
  id: NavGroupId;
  label: string;
  order: number;
};

/** Sidebar section order & Chinese titles. */
export const NAV_GROUPS: NavGroupMeta[] = [
  { id: "overview", label: "运营总览", order: 10 },
  { id: "knowledge", label: "知识中心", order: 20 },
  { id: "intelligence", label: "智能配置", order: 30 },
  { id: "service", label: "客服运营", order: 40 },
  { id: "system", label: "系统治理", order: 50 },
];

/** Static catalog — filtered by enabled features at runtime. */
export const ADMIN_NAV: AdminNavItem[] = [
  {
    pluginId: "analytics",
    to: "/admin",
    label: "运营看板",
    order: 10,
    group: "overview",
    icon: "dashboard",
    hint: "核心运营指标",
  },
  {
    pluginId: "qc",
    to: "/admin/qc",
    label: "质检中心",
    order: 15,
    group: "overview",
    icon: "qc",
    hint: "质量评分与低分回放",
  },
  {
    pluginId: "cost",
    to: "/admin/costs",
    label: "成本分析",
    order: 16,
    group: "overview",
    icon: "cost",
    hint: "模型调用与费用",
  },
  {
    pluginId: "agent",
    to: "/admin/agent-runs",
    label: "运行回放",
    order: 17,
    group: "overview",
    icon: "replay",
    hint: "Agent 步骤与轨迹",
  },
  {
    pluginId: "rag",
    to: "/admin/documents",
    label: "知识文档",
    order: 20,
    group: "knowledge",
    icon: "docs",
    hint: "上传与索引",
  },
  {
    pluginId: "knowledge",
    to: "/admin/gaps",
    label: "知识缺口",
    order: 30,
    group: "knowledge",
    icon: "gap",
    hint: "未覆盖问题",
  },
  {
    pluginId: "knowledge",
    to: "/admin/drafts",
    label: "知识草稿",
    order: 31,
    group: "knowledge",
    icon: "draft",
    hint: "待审 FAQ 草稿",
  },
  {
    pluginId: "ops",
    to: "/admin/intents",
    label: "意图路由",
    order: 21,
    group: "intelligence",
    icon: "intent",
    hint: "意图 → 路由映射",
  },
  {
    pluginId: "ops",
    to: "/admin/prompts",
    label: "提示词模板",
    order: 22,
    group: "intelligence",
    icon: "prompt",
    hint: "Prompt 版本管理",
  },
  {
    pluginId: "handoff",
    to: "/admin/handoffs",
    label: "人工接管",
    order: 40,
    group: "service",
    icon: "handoff",
    hint: "转人工收件箱",
  },
  {
    pluginId: "ticket",
    to: "/admin/tickets",
    label: "工单中心",
    order: 50,
    group: "service",
    icon: "ticket",
    hint: "工单流转",
  },
  {
    pluginId: "teams",
    to: "/admin/teams",
    label: "技能组",
    order: 55,
    group: "service",
    icon: "team",
    hint: "座席分组",
  },
  {
    pluginId: "sla",
    to: "/admin/sla",
    label: "SLA 监控",
    order: 56,
    group: "service",
    icon: "sla",
    hint: "超时与升级",
  },
  {
    pluginId: "core",
    to: "/admin/users",
    label: "用户管理",
    order: 91,
    group: "system",
    icon: "users",
    hint: "账号与角色",
  },
  {
    pluginId: "core",
    to: "/admin/audit",
    label: "审计日志",
    order: 90,
    group: "system",
    icon: "audit",
    hint: "操作留痕",
  },
  {
    pluginId: "connectors",
    to: "/admin/connectors",
    label: "业务连接器",
    order: 92,
    group: "system",
    icon: "connector",
    hint: "外部系统对接",
  },
  {
    pluginId: "launch",
    to: "/admin/launch-cards",
    label: "上线卡片",
    order: 94,
    group: "system",
    icon: "launch",
    hint: "变更与度量",
  },
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

export type NavSection = {
  group: NavGroupMeta;
  items: AdminNavItem[];
};

/** Group filtered nav items into ordered sidebar sections. */
export function groupNav(items: AdminNavItem[]): NavSection[] {
  const byGroup = new Map<NavGroupId, AdminNavItem[]>();
  for (const item of items) {
    const gid = item.group ?? "system";
    const list = byGroup.get(gid) ?? [];
    list.push(item);
    byGroup.set(gid, list);
  }
  return NAV_GROUPS.map((group) => ({
    group,
    items: (byGroup.get(group.id) ?? []).sort(
      (a, b) => a.order - b.order || a.to.localeCompare(b.to)
    ),
  })).filter((s) => s.items.length > 0);
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
