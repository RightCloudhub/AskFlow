import { api } from "../api/client";
import type { Draft } from "../api/types";

export const draftService = {
  list: () => api<Draft[]>("/api/v1/admin/drafts"),

  create: (title: string, content: string) =>
    api("/api/v1/admin/drafts", {
      method: "POST",
      body: JSON.stringify({ title, content }),
    }),

  approve: (id: string) =>
    api(`/api/v1/admin/drafts/${id}/approve`, { method: "POST" }),

  reject: (id: string) =>
    api(`/api/v1/admin/drafts/${id}/reject`, { method: "POST" }),
};
