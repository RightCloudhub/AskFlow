import { FormEvent, useState } from "react";
import { Button, Card, Input, Progress, Space, Table } from "antd";
import { PlusOutlined } from "@ant-design/icons";
import { PageHeader, StatusBadge } from "../../components/admin";
import {
  useCreateLaunchCard,
  useLaunchCards,
} from "../../hooks/use-governance";
import type { LaunchCard } from "../../api/types";

const STATUS_MAP: Record<string, string> = {
  planned: "规划中",
  measuring: "度量中",
  shipped: "已上线",
  draft: "草稿",
};

export function LaunchCardsPage() {
  const [title, setTitle] = useState("");
  const cardsQ = useLaunchCards();
  const create = useCreateLaunchCard();

  async function onCreate(e: FormEvent) {
    e.preventDefault();
    await create.mutateAsync(title);
    setTitle("");
  }

  return (
    <div className="af-page">
      <PageHeader
        eyebrow="系统治理"
        title="上线卡片"
        subtitle="变更发布与关键指标度量"
      />
      <Card title="创建上线卡片" style={{ marginBottom: 16 }}>
        <form onSubmit={(e) => void onCreate(e)}>
          <Space>
            <Input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="变更标题"
              required
              style={{ width: 320 }}
            />
            <Button
              type="primary"
              htmlType="submit"
              icon={<PlusOutlined />}
              loading={create.isPending}
            >
              创建
            </Button>
          </Space>
        </form>
      </Card>

      <Card title="卡片列表">
        <Table
          loading={cardsQ.isLoading}
          rowKey="id"
          dataSource={cardsQ.data ?? []}
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
              render: (_: unknown, c: LaunchCard) => {
                const v = c.expected_metrics?.faq_resolve_rate ?? 0;
                return <Progress percent={Math.round(v * 100)} size="small" />;
              },
            },
            {
              title: "实测 FAQ 解决率",
              key: "measured",
              render: (_: unknown, c: LaunchCard) => {
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
