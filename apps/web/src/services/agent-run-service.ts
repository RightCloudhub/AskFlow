import { api } from "../api/client";
import type { AgentRun, AgentRunDetail } from "../api/types";

export const agentRunService = {
  list: (limit = 50) =>
    api<AgentRun[]>(`/api/v1/admin/agent-runs?limit=${limit}`),

  detail: (runId: string) =>
    api<AgentRunDetail>(`/api/v1/admin/agent-runs/${runId}`),
};
