import { api } from "../api/client";
import type { Draft, Gap } from "../api/types";

export const gapService = {
  list: () => api<Gap[]>("/api/v1/admin/gaps"),

  dismiss: (id: string) =>
    api(`/api/v1/admin/gaps/${id}/dismiss`, { method: "POST" }),

  promote: (g: Gap) =>
    api<Draft>(`/api/v1/admin/gaps/${g.id}/promote`, {
      method: "POST",
      body: JSON.stringify({
        title: `FAQ: ${g.question.slice(0, 40)}`,
        content: g.question,
        gap_id: g.id,
      }),
    }),
};
