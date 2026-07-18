import { api } from "../api/client";
import type { AuditLog } from "../api/types";

export const auditService = {
  list: () => api<AuditLog[]>("/api/v1/admin/audit-logs"),
};
