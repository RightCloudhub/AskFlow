import { api } from "../api/client";
import type { IntentRow } from "../api/types";

export const intentService = {
  list: () => api<IntentRow[]>("/api/v1/admin/intents"),

  upsert: (intent: string, route: string) =>
    api(`/api/v1/admin/intents/${intent}`, {
      method: "PUT",
      body: JSON.stringify({
        intent,
        route,
        enabled: true,
        description: "ops",
      }),
    }),
};
