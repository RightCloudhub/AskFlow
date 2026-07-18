import { Card, Col, Empty, Row, Tag } from "antd";
import type { Ticket } from "../../../api/types";
import { StatusBadge } from "../../admin";

const COLUMNS: { key: string; title: string }[] = [
  { key: "pending", title: "待处理" },
  { key: "processing", title: "处理中" },
  { key: "resolved", title: "已解决" },
  { key: "closed", title: "已关闭" },
];

type TicketBoardProps = {
  rows: Ticket[];
  onSelect?: (t: Ticket) => void;
};

export function TicketBoard({ rows, onSelect }: TicketBoardProps) {
  return (
    <Row gutter={12}>
      {COLUMNS.map((col) => {
        const items = rows.filter((r) => r.status === col.key);
        return (
          <Col key={col.key} xs={24} sm={12} lg={6}>
            <Card
              size="small"
              title={
                <span>
                  {col.title} <Tag>{items.length}</Tag>
                </span>
              }
              className="af-ticket-col"
            >
              {items.length === 0 ? (
                <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="空" />
              ) : (
                items.map((t) => (
                  <button
                    key={t.id}
                    type="button"
                    className="af-ticket-card"
                    onClick={() => onSelect?.(t)}
                  >
                    <strong>{t.title}</strong>
                    <StatusBadge value={t.status} />
                    <span className="meta">{t.priority}</span>
                  </button>
                ))
              )}
            </Card>
          </Col>
        );
      })}
    </Row>
  );
}
