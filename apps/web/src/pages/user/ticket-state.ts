import { useState } from "react";
import { useCloseTicket, useCreateTicket, useTickets } from "../../hooks/use-tickets";
import type { Ticket } from "../../api/types";

export function useTicketsPage() {
  const [view, setView] = useState<"list" | "board">("list");
  const [selected, setSelected] = useState<Ticket | null>(null);
  const tickets = useTickets();
  const create = useCreateTicket();
  const close = useCloseTicket();
  const error = (create.error instanceof Error && create.error.message) ||
    (tickets.error instanceof Error && tickets.error.message) || null;
  const rows = tickets.data ?? [];
  const openCount = rows.filter((ticket) => ticket.status !== "closed" && ticket.status !== "resolved").length;
  return { view, setView, selected, setSelected, tickets, create, close, error, rows, openCount };
}
