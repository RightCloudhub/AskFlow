import { FormEvent, useEffect, useState } from "react";
import { Button, Card, Input, Progress, Space, Table } from "antd";
import { PlusOutlined } from "@ant-design/icons";
import { api } from "../../api/client";
import { PageHeader, StatusBadge } from "../../components/admin";

type CardRow = {
  id: string;
  title: string;
  status: string;
  expected_metrics: Record<string, number>;
  measured_metrics: Record<string, number>;
};

const STATUS_MAP: Record<string, string> = {
  planned: "规划中",
  measuring: "度量中",
  shipped: "已上线",
  draft: "草稿",
};

export function LaunchCardsPage() {
  const [rows, setRows] = useState<CardRow[]>([]);
  const [title, setTitle] = useState("");
  const [loading, setLoading] = useState(true);

  async function load() {
    setRows(await api<CardRow[]>("/api/v1/admin/launch-cards"));
  }

  useEffect(() => {
    void load().finally(() => setLoading(false));
  }, []);

  async function create(e: FormEvent) {
    e.preventDefault();
    await api("/api/v1/admin/launch-cards", {
      method: "POST",
      body: JSON.stringify({
        title,
        expected_metrics: { faq_resolve_rate: 0.7 },
      }),
    });
    setTitle("");
    await load();
  }

  return (
    <div className="af-page">
      <PageHeader
        eyebrow="系统治理"
        title="上线卡片"
        subtitle="变更发布与关键指标度量"
      />
      <Card title="创建上线卡片" style={{ marginBottom: 16 }}>
        <form onSubmit={(e) => void create(e)}>
          <Space>
            <Input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="变更标题"
              required
              style={{ width: 320 }}
            />
            <Button type="primary" htmlType="submit" icon={<PlusOutlined />}>
              创建
            </Button>
          </Space>
        </form>
      </Card>

      <Card title="卡片列表">
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
              width: 120,
              render: (s: string) => (
                <StatusBadge value={s} label={STATUS_MAP[s] ?? s} />
              ),
            },
            {
              title: "预期 FAQ 解决率",
              key: "expected",
              render: (_: unknown, c: CardRow) => {
                const v = c.expected_metrics?.faq_resolve_rate ?? 0;
                return <Progress percent={Math.round(v * 100)} size="small" />;
              },
            },
            {
              title: "实测 FAQ 解决率",
              key: "measured",
              render: (_: unknown, c: CardRow) => {
                const v = c.measured_metrics?.faq_resolve_rate;
                if (v === undefined || v === null) return "—";
                return (
                  <Progress
                    percent={Math.round(v * 100)}
                    size="small"
                    status="active"
                  />
                );
              },
            },
          ]}
          locale={{ emptyText: "暂无上线卡片" }}
        />
      </Card>
    </div>
  );
}
