import { api } from "../api/client";
import type { QcLowRun, QcSummary } from "../api/types";

export const qcService = {
  summary: () => api<QcSummary>("/api/v1/admin/qc/summary"),

  lowQuality: (limit = 30) =>
    api<{ runs: QcLowRun[] }>(`/api/v1/admin/qc/low-quality?limit=${limit}`),
};
