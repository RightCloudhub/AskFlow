import { Button, Card, Space, Table, Typography } from "antd";
import { CheckCircleOutlined, SyncOutlined } from "@ant-design/icons";
import {
  PageHeader,
  PriorityTag,
  StatusBadge,
  ticketTypeLabel,
} from "../../components/admin";
import { useAdminTickets, useUpdateAdminTicket } from "../../hooks/use-ops";
import type { AdminTicket } from "../../api/types";

export function TicketsAdminPage() {
  const ticketsQ = useAdminTickets();
  const update = useUpdateAdminTicket();

  return (
    <div className="af-page">
      <PageHeader
        eyebrow="客服运营"
        title="工单中心"
        subtitle="工单流转与状态更新"
      />
      <Card>
        <Table
          loading={ticketsQ.isLoading}
          rowKey="id"
          dataSource={ticketsQ.data ?? []}
          pagination={{ pageSize: 10 }}
          columns={[
            { title: "标题", dataIndex: "title" },
            {
              title: "状态",
              dataIndex: "status",
              width: 110,
              render: (s: string) => <StatusBadge value={s} />,
            },
            {
              title: "优先级",
              dataIndex: "priority",
              width: 100,
              render: (p: string) => <PriorityTag value={p} />,
            },
            {
              title: "类型",
              dataIndex: "type",
              width: 120,
              render: (t: string) => ticketTypeLabel(t),
            },
            {
              title: "操作",
              key: "actions",
              width: 220,
              render: (_: unknown, t: AdminTicket) => (
                <Space>
                  {t.status === "pending" ? (
                  <Button
                    size="small"
                    icon={<SyncOutlined />}
                    loading={
                      update.isPending &&
                      update.variables?.id === t.id &&
                      update.variables?.status === "processing"
                    }
                    onClick={() =>
                      void update.mutateAsync({
                        id: t.id,
                        status: "processing",
                      })
                    }
                  >
                    处理中
                  </Button>
                  ) : null}
                  {t.status === "pending" || t.status === "processing" ? (
                  <Button
                    type="primary"
                    size="small"
                    icon={<CheckCircleOutlined />}
                    loading={
                      update.isPending &&
                      update.variables?.id === t.id &&
                      update.variables?.status === "resolved"
                    }
                    onClick={() =>
                      void update.mutateAsync({ id: t.id, status: "resolved" })
                    }
                  >
                    标记解决
                  </Button>
                  ) : (
                    <Typography.Text type="secondary">无需操作</Typography.Text>
                  )}
                </Space>
              ),
            },
          ]}
          locale={{ emptyText: "暂无工单" }}
        />
      </Card>
    </div>
  );
}
