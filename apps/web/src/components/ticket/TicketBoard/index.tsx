import type { Ticket } from "../../../api/types";
import { PriorityTag } from "../../admin";

const COLUMNS = [
  { key: "pending", title: "待处理" }, { key: "processing", title: "处理中" },
  { key: "resolved", title: "已解决" }, { key: "closed", title: "已关闭" },
];
type TicketBoardProps = { rows: Ticket[]; onSelect?: (ticket: Ticket) => void };

export function TicketBoard({ rows, onSelect }: TicketBoardProps) {
  return <div className="af-ticket-board">{COLUMNS.map((column) => {
    const items = rows.filter((ticket) => ticket.status === column.key);
    return <section key={column.key} className="af-ticket-col"><header><h3>{column.title}</h3><span>{items.length}</span></header>
      <div className="af-ticket-column-items">{items.map((ticket) => <button key={ticket.id} type="button"
        className="af-ticket-card" onClick={() => onSelect?.(ticket)}>
        <strong>{ticket.title}</strong><span className="af-ticket-card-tags"><PriorityTag value={ticket.priority} /></span>
      </button>)}{!items.length && <p className="af-ticket-board-empty">暂无{column.title}工单</p>}</div>
    </section>;
  })}</div>;
}
