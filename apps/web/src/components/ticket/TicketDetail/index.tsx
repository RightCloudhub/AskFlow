import { Descriptions, Drawer, Tag } from "antd";
import { StatusBadge } from "../../admin";
import type { Ticket } from "../../../api/types";

type TicketDetailProps = {
  open: boolean;
  ticket: Ticket | null;
  onClose: () => void;
};

export function TicketDetail({ open, ticket, onClose }: TicketDetailProps) {
  return (
    <Drawer title="工单详情" open={open} onClose={onClose} width={400} destroyOnClose>
      {!ticket ? null : (
        <Descriptions column={1} size="small" bordered>
          <Descriptions.Item label="标题">{ticket.title}</Descriptions.Item>
          <Descriptions.Item label="状态">
            <StatusBadge value={ticket.status} />
          </Descriptions.Item>
          <Descriptions.Item label="优先级">
            <Tag>{ticket.priority}</Tag>
          </Descriptions.Item>
          <Descriptions.Item label="类型">{ticket.type}</Descriptions.Item>
          <Descriptions.Item label="描述">
            {ticket.description || "—"}
          </Descriptions.Item>
          <Descriptions.Item label="创建时间">
            {ticket.created_at?.slice(0, 19).replace("T", " ") ?? "—"}
          </Descriptions.Item>
        </Descriptions>
      )}
    </Drawer>
  );
}
