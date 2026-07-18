import { useEffect, useState } from "react";
import { Button, Card, Space, Table, Tag } from "antd";
import { CheckOutlined, StopOutlined } from "@ant-design/icons";
import { api } from "../../api/client";
import { PageHeader, StatusBadge } from "../../components/admin";

type Gap = {
  id: string;
  question: string;
  hit_count: number;
  reason: string | null;
  status: string;
};

export function GapsPage() {
  const [gaps, setGaps] = useState<Gap[]>([]);
  const [loading, setLoading] = useState(true);

  async function load() {
    setGaps(await api<Gap[]>("/api/v1/admin/gaps"));
  }

  useEffect(() => {
    void load().finally(() => setLoading(false));
  }, []);

  async function dismiss(id: string) {
    await api(`/api/v1/admin/gaps/${id}/dismiss`, { method: "POST" });
    await load();
  }

  async function promote(g: Gap) {
    await api(`/api/v1/admin/gaps/${g.id}/promote`, {
      method: "POST",
      body: JSON.stringify({
        title: `FAQ: ${g.question.slice(0, 40)}`,
        content: g.question,
        gap_id: g.id,
      }),
    });
    await load();
  }

  return (
    <div className="af-page">
      <PageHeader
        eyebrow="知识中心"
        title="知识缺口"
        subtitle="未覆盖问题沉淀，可生成草稿或忽略"
      />
      <Card>
        <Table
          loading={loading}
          rowKey="id"
          dataSource={gaps}
          pagination={{ pageSize: 10 }}
          columns={[
            { title: "问题", dataIndex: "question" },
            {
              title: "命中",
              dataIndex: "hit_count",
              width: 90,
              render: (n: number) => <Tag color="blue">{n}</Tag>,
            },
            {
              title: "原因",
              dataIndex: "reason",
              render: (r: string | null) => r || "—",
            },
            {
              title: "状态",
              dataIndex: "status",
              width: 100,
              render: (s: string) => <StatusBadge value={s} />,
            },
            {
              title: "操作",
              key: "actions",
              width: 220,
              render: (_: unknown, g: Gap) => (
                <Space>
                  <Button
                    type="primary"
                    size="small"
                    icon={<CheckOutlined />}
                    onClick={() => void promote(g)}
                  >
                    生成草稿
                  </Button>
                  <Button
                    size="small"
                    icon={<StopOutlined />}
                    onClick={() => void dismiss(g.id)}
                  >
                    忽略
                  </Button>
                </Space>
              ),
            },
          ]}
          locale={{ emptyText: "暂无知识缺口" }}
        />
      </Card>
    </div>
  );
}
