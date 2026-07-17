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

export type AdminNavItem = {
  pluginId: FeatureId | string;
  to: string;
  label: string;
  order: number;
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
