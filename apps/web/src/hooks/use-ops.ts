import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { intentService } from "../services/intent-service";
import { promptService } from "../services/prompt-service";
import { handoffService } from "../services/handoff-service";
import { adminTicketService } from "../services/admin-ticket-service";
import { teamService } from "../services/team-service";
import { slaService } from "../services/sla-service";
import {
  HandoffKeys,
  IntentKeys,
  PromptKeys,
  SlaKeys,
  TeamKeys,
  TicketKeys,
} from "./query-keys";

const HANDOFF_POLL_MS = 15_000;

export function useIntents() {
  return useQuery({
    queryKey: IntentKeys.list(),
    queryFn: () => intentService.list(),
  });
}

export function useUpsertIntent() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (p: { intent: string; route: string }) =>
      intentService.upsert(p.intent, p.route),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: IntentKeys.list() });
    },
  });
}

export function usePromptTemplates() {
  return useQuery({
    queryKey: PromptKeys.list(),
    queryFn: () => promptService.list(),
  });
}

export function usePublishPrompt() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (p: { key: string; content: string }) =>
      promptService.publish(p.key, p.content),
    onSuccess: (_d, p) => {
      void qc.invalidateQueries({ queryKey: PromptKeys.list() });
      void qc.invalidateQueries({ queryKey: PromptKeys.active(p.key) });
    },
  });
}

export function useHandoffs() {
  return useQuery({
    queryKey: HandoffKeys.list(),
    queryFn: () => handoffService.list(),
    refetchInterval: HANDOFF_POLL_MS,
  });
}

export function useClaimHandoff() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => handoffService.claim(id),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: HandoffKeys.list() });
    },
  });
}

export function useReturnHandoff() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => handoffService.returnToAi(id),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: HandoffKeys.list() });
    },
  });
}

export function useHandoffMessages(handoffId: string | null) {
  return useQuery({
    queryKey: HandoffKeys.messages(handoffId ?? ""),
    queryFn: () => handoffService.messages(handoffId!),
    enabled: Boolean(handoffId),
    refetchInterval: 8_000,
  });
}

export function useStaffReply() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (p: { id: string; content: string }) =>
      handoffService.reply(p.id, p.content),
    onSuccess: (_d, p) => {
      void qc.invalidateQueries({ queryKey: HandoffKeys.messages(p.id) });
      void qc.invalidateQueries({ queryKey: HandoffKeys.list() });
    },
  });
}

export function useAdminTickets() {
  return useQuery({
    queryKey: TicketKeys.adminList(),
    queryFn: () => adminTicketService.list(),
  });
}

export function useUpdateAdminTicket() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (p: { id: string; status: string }) =>
      adminTicketService.updateStatus(p.id, p.status),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: TicketKeys.adminList() });
    },
  });
}

export function useTeams() {
  return useQuery({
    queryKey: TeamKeys.list(),
    queryFn: () => teamService.list(),
  });
}

export function useCreateTeam() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (p: { name: string; scope: string }) =>
      teamService.create(p.name, p.scope),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: TeamKeys.list() });
    },
  });
}

export function useAddTeamMember() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (p: { teamId: string; userId: string }) =>
      teamService.addMember(p.teamId, p.userId),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: TeamKeys.list() });
    },
  });
}

export function useSlaStatus() {
  return useQuery({
    queryKey: SlaKeys.status(),
    queryFn: () => slaService.status(),
  });
}

export function useSlaScan() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => slaService.scan(),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: SlaKeys.status() });
    },
  });
}
