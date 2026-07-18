import { api } from "../api/client";
import type { CostSummary } from "../api/types";

export const costService = {
  summary: () => api<CostSummary>("/api/v1/admin/costs/summary"),
};
