import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { gapService } from "../services/gap-service";
import { draftService } from "../services/draft-service";
import type { Gap } from "../api/types";
import { DraftKeys, GapKeys } from "./query-keys";

export function useGaps() {
  return useQuery({
    queryKey: GapKeys.list(),
    queryFn: () => gapService.list(),
  });
}

export function useDismissGap() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => gapService.dismiss(id),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: GapKeys.list() });
    },
  });
}

export function usePromoteGap() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (g: Gap) => gapService.promote(g),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: GapKeys.list() });
      void qc.invalidateQueries({ queryKey: DraftKeys.list() });
    },
  });
}

export function useDrafts() {
  return useQuery({
    queryKey: DraftKeys.list(),
    queryFn: () => draftService.list(),
  });
}

export function useCreateDraft() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (p: { title: string; content: string }) =>
      draftService.create(p.title, p.content),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: DraftKeys.list() });
    },
  });
}

export function useApproveDraft() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => draftService.approve(id),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: DraftKeys.list() });
    },
  });
}

export function useRejectDraft() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => draftService.reject(id),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: DraftKeys.list() });
    },
  });
}
