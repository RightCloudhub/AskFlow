import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { auditService } from "../services/audit-service";
import { userService } from "../services/user-service";
import { connectorService } from "../services/connector-service";
import { costService } from "../services/cost-service";
import { launchService } from "../services/launch-service";
import { agentRunService } from "../services/agent-run-service";
import { qcService } from "../services/qc-service";
import type { User } from "../api/types";
import {
  AgentRunKeys,
  AuditKeys,
  ConnectorKeys,
  CostKeys,
  LaunchKeys,
  QcKeys,
  UserKeys,
} from "./query-keys";

export function useAuditLogs() {
  return useQuery({
    queryKey: AuditKeys.list(),
    queryFn: () => auditService.list(),
  });
}

export function useUsers() {
  return useQuery({
    queryKey: UserKeys.list(),
    queryFn: () => userService.list(),
  });
}

export function useToggleUser() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (u: User) => userService.setActive(u.id, !Boolean(u.is_active)),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: UserKeys.list() });
    },
  });
}

export function useConnectors() {
  return useQuery({
    queryKey: ConnectorKeys.list(),
    queryFn: () => connectorService.list(),
  });
}

export function useInvokeConnector() {
  return useMutation({
    mutationFn: (name: string) => connectorService.invoke(name),
  });
}

export function useCostSummary() {
  return useQuery({
    queryKey: CostKeys.summary(),
    queryFn: () => costService.summary(),
    staleTime: 30_000,
  });
}

export function useLaunchCards() {
  return useQuery({
    queryKey: LaunchKeys.list(),
    queryFn: () => launchService.list(),
  });
}

export function useCreateLaunchCard() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (title: string) => launchService.create(title),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: LaunchKeys.list() });
    },
  });
}

export function useAgentRuns() {
  return useQuery({
    queryKey: AgentRunKeys.list(),
    queryFn: () => agentRunService.list(),
  });
}

export function useAgentRunDetail(runId: string | null) {
  return useQuery({
    queryKey: AgentRunKeys.detail(runId ?? ""),
    queryFn: () => agentRunService.detail(runId!),
    enabled: Boolean(runId),
  });
}

export function useQcSummary() {
  return useQuery({
    queryKey: QcKeys.summary(),
    queryFn: () => qcService.summary(),
  });
}

export function useQcLowQuality() {
  return useQuery({
    queryKey: QcKeys.lowQuality(),
    queryFn: async () => (await qcService.lowQuality()).runs || [],
  });
}
