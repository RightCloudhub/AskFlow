import { api } from "../api/client";
import type { User } from "../api/types";

export const authService = {
  me: () => api<User>("/api/v1/admin/auth/me"),

  login: (username: string, password: string) =>
    api<{ access_token: string }>("/api/v1/admin/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    }),

  register: (username: string, email: string, password: string) =>
    api("/api/v1/admin/auth/register", {
      method: "POST",
      body: JSON.stringify({ username, email, password }),
    }),
};
