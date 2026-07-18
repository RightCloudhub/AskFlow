import { api } from "../api/client";
import type { Team } from "../api/types";

export const teamService = {
  list: () => api<Team[]>("/api/v1/admin/teams"),

  create: (name: string, intent_scope: string) =>
    api("/api/v1/admin/teams", {
      method: "POST",
      body: JSON.stringify({ name, intent_scope, description: "" }),
    }),

  addMember: (teamId: string, userId: string) =>
    api(`/api/v1/admin/teams/${teamId}/members`, {
      method: "POST",
      body: JSON.stringify({ user_id: userId }),
    }),
};
