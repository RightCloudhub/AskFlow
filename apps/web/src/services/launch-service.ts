import { api } from "../api/client";
import type { LaunchCard } from "../api/types";

export const launchService = {
  list: () => api<LaunchCard[]>("/api/v1/admin/launch-cards"),

  create: (title: string) =>
    api("/api/v1/admin/launch-cards", {
      method: "POST",
      body: JSON.stringify({
        title,
        expected_metrics: { faq_resolve_rate: 0.7 },
      }),
    }),
};
