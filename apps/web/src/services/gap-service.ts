import { api } from "../api/client";
import type { Draft, Gap } from "../api/types";

export type GapPromotion = { id: string; title: string; content: string };

export const gapService = {
  list: () => api<Gap[]>("/api/v1/admin/gaps"),

  dismiss: (id: string) =>
    api(`/api/v1/admin/gaps/${id}/dismiss`, { method: "POST" }),

  promote: (draft: GapPromotion) =>
    api<Draft>(`/api/v1/admin/gaps/${draft.id}/promote`, {
      method: "POST",
      body: JSON.stringify({
        title: draft.title,
        content: draft.content,
        gap_id: draft.id,
      }),
    }),
};
