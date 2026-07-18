import { api } from "../api/client";
import type { SlaScanResult, SlaStatus } from "../api/types";

export const slaService = {
  status: () => api<SlaStatus>("/api/v1/admin/sla/status"),

  scan: () =>
    api<SlaScanResult>("/api/v1/admin/sla/scan", { method: "POST" }),
};
