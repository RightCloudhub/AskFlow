import { Button, Card, Space, Table } from "antd";
import { CheckCircleOutlined, SyncOutlined } from "@ant-design/icons";
import { PageHeader, StatusBadge } from "../../components/admin";
import {
  useAdminTickets,
  useUpdateAdminTicket,
} from "../../hooks/use-ops";
import type { AdminTicket } from "../../api/types";

const PRIORITY: Record<string, string> = {
  low: "低",
  normal: "普通",
  medium: "中",
  high: "高",
  urgent: "紧急",
};

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
              render: (p: string) => PRIORITY[p] ?? p,
            },
            { title: "类型", dataIndex: "type", width: 120 },
            {
              title: "操作",
              key: "actions",
              width: 220,
              render: (_: unknown, t: AdminTicket) => (
                <Space>
                  <Button
                    size="small"
                    icon={<SyncOutlined />}
                    loading={
                      update.isPending &&
                      update.variables?.id === t.id &&
                      update.variables?.status === "processing"
                    }
                    onClick={() =>
                      void update.mutateAsync({ id: t.id, status: "processing" })
                    }
                  >
                    处理中
                  </Button>
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
                    已解决
                  </Button>
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
