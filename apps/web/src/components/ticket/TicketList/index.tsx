import { Button, Table, Tag } from "antd";
import { StatusBadge } from "../../admin";
import type { Ticket } from "../../../api/types";

type TicketListProps = {
  rows: Ticket[];
  loading?: boolean;
  closingId?: string | null;
  onClose?: (id: string) => void;
  showClose?: boolean;
};

export function TicketList({
  rows,
  loading,
  closingId,
  onClose,
  showClose = true,
}: TicketListProps) {
  return (
    <Table<Ticket>
      rowKey="id"
      loading={loading}
      dataSource={rows}
      pagination={{ pageSize: 8 }}
      columns={[
        { title: "标题", dataIndex: "title" },
        {
          title: "状态",
          dataIndex: "status",
          render: (s: string) => <StatusBadge value={s} />,
        },
        {
          title: "优先级",
          dataIndex: "priority",
          render: (p: string) => <Tag>{p}</Tag>,
        },
        {
          title: "创建时间",
          dataIndex: "created_at",
          render: (t: string) => t?.slice(0, 19).replace("T", " ") ?? "—",
        },
        ...(showClose && onClose
          ? [
              {
                title: "操作",
                key: "actions",
                render: (_: unknown, row: Ticket) =>
                  row.status !== "closed" ? (
                    <Button
                      size="small"
                      loading={closingId === row.id}
                      onClick={() => onClose(row.id)}
                    >
                      关闭
                    </Button>
                  ) : (
                    "—"
                  ),
              },
            ]
          : []),
      ]}
      locale={{ emptyText: "暂无工单" }}
    />
  );
}
