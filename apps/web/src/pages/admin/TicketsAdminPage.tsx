import { useEffect, useState } from "react";
import { Button, Card, Space, Table } from "antd";
import { CheckCircleOutlined, SyncOutlined } from "@ant-design/icons";
import { api } from "../../api/client";
import { PageHeader, StatusBadge } from "../../components/admin";

type Ticket = {
  id: string;
  title: string;
  status: string;
  priority: string;
  type: string;
  assignee: string | null;
};

const PRIORITY: Record<string, string> = {
  low: "低",
  normal: "普通",
  high: "高",
  urgent: "紧急",
};

export function TicketsAdminPage() {
  const [rows, setRows] = useState<Ticket[]>([]);
  const [loading, setLoading] = useState(true);

  async function load() {
    setRows(await api<Ticket[]>("/api/v1/admin/tickets"));
  }

  useEffect(() => {
    void load().finally(() => setLoading(false));
  }, []);

  async function setStatus(id: string, status: string) {
    await api(`/api/v1/admin/tickets/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ status }),
    });
    await load();
  }

  return (
    <div className="af-page">
      <PageHeader
        eyebrow="客服运营"
        title="工单中心"
        subtitle="工单流转与状态更新"
      />
      <Card>
        <Table
          loading={loading}
          rowKey="id"
          dataSource={rows}
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
              render: (_: unknown, t: Ticket) => (
                <Space>
                  <Button
                    size="small"
                    icon={<SyncOutlined />}
                    onClick={() => void setStatus(t.id, "processing")}
                  >
                    处理中
                  </Button>
                  <Button
                    type="primary"
                    size="small"
                    icon={<CheckCircleOutlined />}
                    onClick={() => void setStatus(t.id, "resolved")}
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
