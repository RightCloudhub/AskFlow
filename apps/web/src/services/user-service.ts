import { api } from "../api/client";
import type { User } from "../api/types";

export const userService = {
  list: () => api<User[]>("/api/v1/admin/users"),

  setActive: (id: string, is_active: boolean) =>
    api(`/api/v1/admin/users/${id}/active`, {
      method: "PATCH",
      body: JSON.stringify({ is_active }),
    }),
};
