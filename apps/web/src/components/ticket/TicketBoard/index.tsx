import { Card, Col, Empty, Row } from "antd";
import type { Ticket } from "../../../api/types";
import { PriorityTag, StatusBadge } from "../../admin";

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
    <Row gutter={[12, 12]}>
      {COLUMNS.map((col) => {
        const items = rows.filter((r) => r.status === col.key);
        return (
          <Col key={col.key} xs={24} sm={12} xxl={6}>
            <Card
              size="small"
              title={
                <span>
                  {col.title}{" "}
                  <span className="af-count-pill">{items.length}</span>
                </span>
              }
              className="af-ticket-col"
            >
              {items.length === 0 ? (
                <Empty
                  image={Empty.PRESENTED_IMAGE_SIMPLE}
                  description="暂无"
                />
              ) : (
                items.map((t) => (
                  <button
                    key={t.id}
                    type="button"
                    className="af-ticket-card"
                    onClick={() => onSelect?.(t)}
                  >
                    <strong>{t.title}</strong>
                    <span className="af-ticket-card-tags">
                      <StatusBadge value={t.status} />
                      <PriorityTag value={t.priority} />
                    </span>
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
