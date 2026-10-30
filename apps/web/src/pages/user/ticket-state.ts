import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useCloseTicket, useCreateTicket, useTickets } from "../../hooks/use-tickets";
import type { Ticket } from "../../api/types";
import { useActionFeedback } from "../../components/common/action-feedback";
import { useRecordFilter } from "../../components/admin/use-record-filter";

export function useTicketsPage() {
  const [view, setView] = useState<"list" | "board">("list");
  const [params, setParams] = useSearchParams();
  const tickets = useTickets();
  const create = useCreateTicket();
  const close = useCloseTicket();
  const feedback = useActionFeedback();
  const allRows = tickets.data ?? [];
  const filter = useRecordFilter({ rows: allRows, fields: ["title", "description", "id"], statusField: "status" });
  const openCount = allRows.filter((ticket) => ticket.status !== "closed" && ticket.status !== "resolved").length;
  const selected = allRows.find((ticket) => ticket.id === params.get("ticket_id")) ?? null;
  function setSelected(ticket: Ticket | null) {
    setParams((current) => {
      if (ticket) current.set("ticket_id", ticket.id); else current.delete("ticket_id");
      return current;
    }, { replace: true });
  }
  async function closeTicket(id: string) { await feedback.run(() => close.mutateAsync(id), "工单已关闭。"); }
  return { view, setView, selected, setSelected, tickets, create, close, feedback, filter,
    rows: filter.rows, allRows, openCount, closeTicket };
}
