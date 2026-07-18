import { api, apiForm } from "../api/client";
import type {
  DocumentGenerations,
  DocumentRow,
  GenerationDiff,
} from "../api/types";

export const documentService = {
  list: () => api<DocumentRow[]>("/api/v1/admin/documents"),

  remove: (id: string) =>
    api(`/api/v1/admin/documents/${id}`, { method: "DELETE" }),

  upload: (form: FormData) =>
    apiForm<unknown>("/api/v1/embedding/upload", form),

  generations: (id: string) =>
    api<DocumentGenerations>(`/api/v1/admin/documents/${id}/generations`),

  diff: (id: string, from: number, to: number) =>
    api<GenerationDiff>(
      `/api/v1/admin/documents/${id}/diff?from_generation=${from}&to_generation=${to}`,
    ),

  rollback: (id: string, targetGeneration: number) =>
    api<DocumentRow>(
      `/api/v1/admin/documents/${id}/rollback?target_generation=${targetGeneration}`,
      { method: "POST" },
    ),
};
