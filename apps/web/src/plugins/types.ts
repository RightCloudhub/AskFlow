export type FeatureId =
  | "core"
  | "rag"
  | "agent"
  | "tools"
  | "ticket"
  | "handoff"
  | "knowledge"
  | "ops"
  | "cost"
  | "sla"
  | "notify"
  | "sso"
  | "teams"
  | "connectors"
  | "launch"
  | "analytics"
  | "mcp"
  | "widget"
  | "feishu"
  | "qc";

/** Sidebar section key — drives grouped navigation. */
export type NavGroupId =
  | "overview"
  | "knowledge"
  | "intelligence"
  | "service"
  | "system";

export type AdminNavItem = {
  pluginId: FeatureId | string;
  to: string;
  label: string;
  order: number;
  /** Group for collapsible sidebar sections */
  group?: NavGroupId;
  /** Optional short description shown on hover / subtitle */
  hint?: string;
  /** Simple icon key resolved in AdminLayout */
  icon?: string;
};

export type AdminRouteDef = {
  path: string;
  pluginId: FeatureId | string;
  /** lazy page key */
  page: string;
};

export type FeaturesResponse = {
  profile: string;
  features: string[];
  loaded: string[];
  admin_nav: { plugin_id: string; to: string; label: string; order: number }[];
  route_handlers: string[];
  side_effects: string[];
};
