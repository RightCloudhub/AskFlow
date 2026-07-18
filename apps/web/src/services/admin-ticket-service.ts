import { api } from "../api/client";
import type { AdminTicket } from "../api/types";

export const adminTicketService = {
  list: () => api<AdminTicket[]>("/api/v1/admin/tickets"),

  updateStatus: (id: string, status: string) =>
    api(`/api/v1/admin/tickets/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ status }),
    }),
};
