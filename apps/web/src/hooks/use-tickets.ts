import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ticketService } from "../services/ticket-service";
import { TicketKeys } from "./query-keys";

export function useTickets() {
  return useQuery({
    queryKey: TicketKeys.list(),
    queryFn: () => ticketService.list(),
  });
}

export function useCreateTicket() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (p: { title: string; description: string }) =>
      ticketService.create(p.title, p.description),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: TicketKeys.list() });
    },
  });
}

export function useCloseTicket() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => ticketService.close(id),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: TicketKeys.list() });
    },
  });
}
