import { api } from "../api/client";
import type { Ticket } from "../api/types";

export const ticketService = {
  list: () => api<Ticket[]>("/api/v1/tickets"),

  create: (title: string, description: string) =>
    api("/api/v1/tickets", {
      method: "POST",
      body: JSON.stringify({
        title,
        description,
        type: "user_created",
        priority: "medium",
      }),
    }),

  close: (id: string) =>
    api(`/api/v1/tickets/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ status: "closed" }),
    }),
};
