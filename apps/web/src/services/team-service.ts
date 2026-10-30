import { api } from "../api/client";
import type { Team } from "../api/types";

export const teamService = {
  list: () => api<Team[]>("/api/v1/admin/teams"),

  create: (name: string, intent_scope: string) =>
    api<Pick<Team, "id" | "name" | "intent_scope">>("/api/v1/admin/teams", {
      method: "POST",
      body: JSON.stringify({ name, intent_scope, description: "" }),
    }).then((team): Team => ({ ...team, description: "", member_ids: [], member_count: 0 })),

  addMember: (teamId: string, userId: string) =>
    api(`/api/v1/admin/teams/${teamId}/members`, {
      method: "POST",
      body: JSON.stringify({ user_id: userId }),
    }),
};
