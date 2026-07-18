import { api } from "../api/client";
import type { AnalyticsSummary } from "../api/types";

export const analyticsService = {
  summary: () =>
    api<AnalyticsSummary>("/api/v1/admin/analytics/summary"),
};
