import { api } from "../api/client";
import type { Handoff, Message } from "../api/types";

export const handoffService = {
  list: () => api<Handoff[]>("/api/v1/admin/handoffs"),

  claim: (id: string) =>
    api<Handoff>(`/api/v1/admin/handoffs/${id}/claim`, { method: "POST" }),

  returnToAi: (id: string) =>
    api<Handoff>(`/api/v1/admin/handoffs/${id}/return`, { method: "POST" }),

  messages: (id: string) =>
    api<Message[]>(`/api/v1/admin/handoffs/${id}/messages`),

  reply: (id: string, content: string) =>
    api<Message>(`/api/v1/admin/handoffs/${id}/reply`, {
      method: "POST",
      body: JSON.stringify({ content }),
    }),
};
