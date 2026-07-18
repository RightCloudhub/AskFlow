import { api } from "../api/client";
import type { PromptTemplate } from "../api/types";

export const promptService = {
  list: () => api<PromptTemplate[]>("/api/v1/admin/prompts"),

  active: (key: string) =>
    api<{ content: string }>(`/api/v1/admin/prompts/${key}/active`),

  publish: (key: string, content: string) =>
    api(`/api/v1/admin/prompts/${key}/versions`, {
      method: "POST",
      body: JSON.stringify({ content, activate: true }),
    }),
};
