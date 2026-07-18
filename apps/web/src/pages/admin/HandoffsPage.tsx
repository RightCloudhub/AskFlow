import { useEffect, useState } from "react";
import { Alert, Button, Card, Space, Table } from "antd";
import { UserSwitchOutlined, RollbackOutlined } from "@ant-design/icons";
import { api } from "../../api/client";
import { PageHeader, StatusBadge } from "../../components/admin";

type Handoff = {
  id: string;
  conversation_id: string;
  status: string;
  summary: string;
  claimed_by: string | null;
};

export function HandoffsPage() {
  const [rows, setRows] = useState<Handoff[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  async function load() {
    setRows(await api<Handoff[]>("/api/v1/admin/handoffs"));
  }

  useEffect(() => {
    void load()
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  }, []);

  async function claim(id: string) {
    try {
      await api(`/api/v1/admin/handoffs/${id}/claim`, { method: "POST" });
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "认领失败");
    }
  }

  async function ret(id: string) {
    await api(`/api/v1/admin/handoffs/${id}/return`, { method: "POST" });
    await load();
  }

  return (
    <div className="af-page">
      <PageHeader
        eyebrow="客服运营"
        title="人工接管"
        subtitle="转人工收件箱 — 认领会话或交还 AI"
      />
      {error ? (
        <Alert type="error" showIcon message={error} style={{ marginBottom: 16 }} />
      ) : null}
      <Card>
        <Table
          loading={loading}
          rowKey="id"
          dataSource={rows}
          pagination={{ pageSize: 10 }}
          columns={[
            {
              title: "状态",
              dataIndex: "status",
              width: 110,
              render: (s: string) => <StatusBadge value={s} />,
            },
            {
              title: "会话",
              dataIndex: "conversation_id",
              render: (id: string) => <code className="af-mono">{id}</code>,
            },
            { title: "摘要", dataIndex: "summary" },
            {
              title: "操作",
              key: "actions",
              width: 220,
              render: (_: unknown, h: Handoff) => (
                <Space>
                  <Button
                    type="primary"
                    size="small"
                    icon={<UserSwitchOutlined />}
                    onClick={() => void claim(h.id)}
                  >
                    认领
                  </Button>
                  <Button
                    size="small"
                    icon={<RollbackOutlined />}
                    onClick={() => void ret(h.id)}
                  >
                    交还 AI
                  </Button>
                </Space>
              ),
            },
          ]}
          locale={{ emptyText: "暂无接管会话" }}
        />
      </Card>
    </div>
  );
}
