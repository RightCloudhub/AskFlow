/** Query key factories — never inline raw arrays (RAGFlow convention). */

export const AuthKeys = {
  me: () => ["auth", "me"] as const,
};

export const ChatKeys = {
  conversations: () => ["chat", "conversations"] as const,
  messages: (conversationId: string) =>
    ["chat", "messages", conversationId] as const,
};

export const DocumentKeys = {
  list: () => ["documents", "list"] as const,
  generations: (id: string) => ["documents", "generations", id] as const,
  diff: (id: string, from: number, to: number) =>
    ["documents", "diff", id, from, to] as const,
};

export const AnalyticsKeys = {
  summary: () => ["analytics", "summary"] as const,
};

export const TicketKeys = {
  list: () => ["tickets", "list"] as const,
  adminList: () => ["tickets", "admin"] as const,
};

export const IntentKeys = {
  list: () => ["intents", "list"] as const,
};

export const PromptKeys = {
  list: () => ["prompts", "list"] as const,
  active: (key: string) => ["prompts", "active", key] as const,
};

export const GapKeys = {
  list: () => ["gaps", "list"] as const,
};

export const DraftKeys = {
  list: () => ["drafts", "list"] as const,
};

export const HandoffKeys = {
  list: () => ["handoffs", "list"] as const,
  messages: (id: string) => ["handoffs", "messages", id] as const,
};

export const AuditKeys = {
  list: () => ["audit", "list"] as const,
};

export const UserKeys = {
  list: () => ["users", "list"] as const,
};

export const ConnectorKeys = {
  list: () => ["connectors", "list"] as const,
};

export const CostKeys = {
  summary: () => ["costs", "summary"] as const,
};

export const LaunchKeys = {
  list: () => ["launch-cards", "list"] as const,
};

export const TeamKeys = {
  list: () => ["teams", "list"] as const,
};

export const SlaKeys = {
  status: () => ["sla", "status"] as const,
};

export const AgentRunKeys = {
  list: () => ["agent-runs", "list"] as const,
  detail: (id: string) => ["agent-runs", "detail", id] as const,
};

export const QcKeys = {
  summary: () => ["qc", "summary"] as const,
  lowQuality: () => ["qc", "low-quality"] as const,
};
