import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { documentService } from "../services/document-service";
import { DocumentKeys } from "./query-keys";

export function useDocuments() {
  return useQuery({
    queryKey: DocumentKeys.list(),
    queryFn: () => documentService.list(),
  });
}

export function useDocumentGenerations(id: string | null) {
  return useQuery({
    queryKey: DocumentKeys.generations(id ?? ""),
    queryFn: () => documentService.generations(id!),
    enabled: Boolean(id),
  });
}

export function useDocumentDiff(
  id: string | null,
  from: number | null,
  to: number | null,
) {
  return useQuery({
    queryKey: DocumentKeys.diff(id ?? "", from ?? 0, to ?? 0),
    queryFn: () => documentService.diff(id!, from!, to!),
    enabled: Boolean(id && from != null && to != null && from !== to),
  });
}

export function useUploadDocument() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (form: FormData) => documentService.upload(form),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: DocumentKeys.list() });
    },
  });
}

export function useDeleteDocument() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => documentService.remove(id),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: DocumentKeys.list() });
    },
  });
}

export function useRollbackDocument() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (p: { id: string; generation: number }) =>
      documentService.rollback(p.id, p.generation),
    onSuccess: (_d, p) => {
      void qc.invalidateQueries({ queryKey: DocumentKeys.list() });
      void qc.invalidateQueries({ queryKey: DocumentKeys.generations(p.id) });
    },
  });
}
