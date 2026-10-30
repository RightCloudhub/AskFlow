import { Button, Popconfirm } from "antd";
import type { TableColumnsType } from "antd";
import { PriorityTag, StatusBadge } from "../../admin";
import { DataTable } from "../../admin/workspace";
import type { Ticket } from "../../../api/types";
import { formatDateTime } from "../../../utils";

type TicketListProps = { rows: Ticket[]; loading?: boolean; closingId?: string | null;
  onClose?: (id: string) => void; showClose?: boolean; onSelect?: (ticket: Ticket) => void };

function CloseAction({ ticket, props }: { ticket: Ticket; props: TicketListProps }) {
  if (ticket.status === "closed") return <span className="af-record-secondary">—</span>;
  return <Popconfirm title="关闭这个工单？" description="关闭后，客服将不再跟进此工单。" okText="关闭工单" cancelText="继续跟进"
    onConfirm={() => props.onClose?.(ticket.id)}><Button type="text" size="small" loading={props.closingId === ticket.id}
      disabled={Boolean(props.closingId) && props.closingId !== ticket.id}>关闭</Button></Popconfirm>;
}

function columns(props: TicketListProps): TableColumnsType<Ticket> {
  const result: TableColumnsType<Ticket> = [
    { title: "问题", dataIndex: "title", render: (title: string, ticket) => <div className="af-record-title">
      {props.onSelect ? <Button type="text" className="af-ticket-title-link" onClick={() => props.onSelect?.(ticket)}>{title}</Button> : <strong>{title}</strong>}
      <small>{ticket.description || "暂无详细描述"}</small></div> },
    { title: "状态", dataIndex: "status", render: (status: string) => <StatusBadge value={status} /> },
    { title: "优先级", dataIndex: "priority", render: (priority: string) => <PriorityTag value={priority} /> },
    { title: "创建时间", dataIndex: "created_at", render: (time: string) => formatDateTime(time) },
  ];
  if (props.showClose !== false && props.onClose) result.push({ title: "操作", key: "actions", render: (_, ticket) => <CloseAction ticket={ticket} props={props} /> });
  return result;
}

export function TicketList(props: TicketListProps) {
  return <DataTable<Ticket> loading={props.loading} dataSource={props.rows} columns={columns(props)}
    emptyTitle="暂无工单" emptyDescription="提交问题后，客服会在这里继续跟进。" />;
}
