import { api } from "../api/client";
import type { Connector } from "../api/types";

export const connectorService = {
  list: () => api<Connector[]>("/api/v1/admin/connectors"),

  invoke: (name: string) =>
    api<Record<string, unknown>>(`/api/v1/admin/connectors/${name}/invoke`, {
      method: "POST",
      body: JSON.stringify({ params: {} }),
    }),
};
