/** Shared API entity types (response shapes). */

export type User = {
  id: string;
  username: string;
  email: string;
  role: string;
  is_active?: boolean;
};

export type Conversation = {
  id: string;
  title: string;
  status: string;
};

export type CitationSource = {
  source?: string;
  text?: string;
  index?: number;
  score?: number;
};

export type Message = {
  id: string;
  role: string;
  content: string;
  meta?: Record<string, unknown>;
  created_at: string;
};

export type DocumentRow = {
  id: string;
  title: string;
  filename: string;
  status: string;
  chunk_count: number;
  generation?: number;
  error_message?: string | null;
};

export type DocumentGenerations = {
  document_id: string;
  current_generation: number;
  generations: number[];
};

export type GenerationDiff = {
  document_id: string;
  from_generation: number;
  to_generation: number;
  added: string[];
  removed: string[];
  unchanged_count: number;
  from_chunk_count?: number;
  to_chunk_count?: number;
};

export type Ticket = {
  id: string;
  title: string;
  status: string;
  priority: string;
  type: string;
  description: string;
  created_at: string;
  assignee?: string | null;
};

export type AdminTicket = {
  id: string;
  title: string;
  status: string;
  priority: string;
  type: string;
  assignee: string | null;
};

export type CostBucket = {
  purpose?: string;
  model?: string;
  estimated_usd: number;
  calls: number;
  prompt_tokens?: number;
  completion_tokens?: number;
};

export type AnalyticsSummary = {
  messages?: number;
  tickets_open?: number;
  handoffs_queued?: number;
  gaps_open?: number;
  thumbs_down?: number;
  sla_breached?: number;
  handoff_timeouts?: number;
  notifications?: number;
  cost_estimated_usd?: number;
  cost?: { by_purpose?: CostBucket[]; by_model?: CostBucket[] };
};

export type CostSummary = {
  by_purpose?: CostBucket[];
  by_model?: CostBucket[];
};

export type SendMessageResult = {
  user_message: Message;
  assistant_message: Message;
};

export type IntentRow = {
  id: string;
  intent: string;
  route: string;
  enabled: boolean;
  description: string;
};

export type PromptTemplate = {
  id: string;
  key: string;
  description: string;
  active_version_id: string | null;
};

export type Gap = {
  id: string;
  question: string;
  hit_count: number;
  reason: string | null;
  status: string;
};

export type Draft = {
  id: string;
  title: string;
  content: string;
  status: string;
  document_id: string | null;
};

export type Handoff = {
  id: string;
  conversation_id: string;
  user_id?: string;
  status: string;
  summary: string;
  intent?: string;
  claimed_by: string | null;
  claimed_at?: string | null;
  created_at?: string;
};

export type AuditLog = {
  id: string;
  action: string;
  resource_type: string;
  resource_id: string | null;
  detail: Record<string, unknown>;
  created_at: string;
};

export type Connector = {
  name: string;
  base_url: string;
  enabled: boolean;
  description: string;
};

export type LaunchCard = {
  id: string;
  title: string;
  status: string;
  expected_metrics: Record<string, number>;
  measured_metrics: Record<string, number>;
};

export type Team = {
  id: string;
  name: string;
  description: string;
  intent_scope: string;
  member_ids?: string[];
  member_count?: number;
};

export type SlaStatus = {
  counts: Record<string, number>;
  tickets: Array<{
    id: string;
    title: string;
    priority: string;
    status: string;
    sla_state: string;
    created_at?: string | null;
  }>;
};

export type SlaScanResult = {
  scanned_changes: number;
  changes: Array<{
    ticket_id: string;
    previous: string;
    current: string;
    reason: string;
  }>;
};

export type AgentRunStep = {
  kind: string;
  name: string;
  detail?: Record<string, unknown>;
};

export type AgentRun = {
  run_id: string;
  route: string;
  intent: string | null;
  refused: boolean;
  flags: string[];
  steps: AgentRunStep[];
  cost_summary: Record<string, unknown>;
  created_at?: string | null;
};

export type AgentRunDetail = AgentRun & {
  cost?: {
    estimated_usd: number;
    entry_count: number;
    entries: Array<Record<string, unknown>>;
  };
};

export type QcSummary = {
  agent_runs?: number;
  refused_runs?: number;
  refuse_rate?: number;
  thumbs_up?: number;
  thumbs_down?: number;
  thumbs_down_rate?: number;
  handoffs?: number;
  messages?: number;
  quality_score_avg?: number | null;
};

export type QcLowRun = {
  run_id: string;
  route: string;
  intent: string | null;
  refused: boolean;
  score: number;
  flags: string[];
};
