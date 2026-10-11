import { Descriptions, Drawer } from "antd";
import { PriorityTag, StatusBadge, ticketTypeLabel } from "../../admin";
import type { Ticket } from "../../../api/types";
import { formatDateTime } from "../../../utils";

type TicketDetailProps = {
  open: boolean;
  ticket: Ticket | null;
  onClose: () => void;
};

export function TicketDetail({ open, ticket, onClose }: TicketDetailProps) {
  return (
    <Drawer
      title="工单详情"
      open={open}
      onClose={onClose}
      size="min(420px, 100vw)"
      destroyOnHidden
    >
      {!ticket ? null : (
        <Descriptions column={1} size="small" bordered>
          <Descriptions.Item label="标题">{ticket.title}</Descriptions.Item>
          <Descriptions.Item label="状态">
            <StatusBadge value={ticket.status} />
          </Descriptions.Item>
          <Descriptions.Item label="优先级">
            <PriorityTag value={ticket.priority} />
          </Descriptions.Item>
          <Descriptions.Item label="类型">
            {ticketTypeLabel(ticket.type)}
          </Descriptions.Item>
          <Descriptions.Item label="描述">
            {ticket.description || "—"}
          </Descriptions.Item>
          <Descriptions.Item label="创建时间">
            {formatDateTime(ticket.created_at, true)}
          </Descriptions.Item>
        </Descriptions>
      )}
    </Drawer>
  );
}
