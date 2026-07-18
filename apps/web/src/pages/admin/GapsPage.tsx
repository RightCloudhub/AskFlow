import { Button, Card, Space, Table, Tag } from "antd";
import { CheckOutlined, StopOutlined } from "@ant-design/icons";
import { PageHeader, StatusBadge } from "../../components/admin";
import {
  useDismissGap,
  useGaps,
  usePromoteGap,
} from "../../hooks/use-knowledge";
import type { Gap } from "../../api/types";

export function GapsPage() {
  const gapsQ = useGaps();
  const dismiss = useDismissGap();
  const promote = usePromoteGap();

  return (
    <div className="af-page">
      <PageHeader
        eyebrow="知识中心"
        title="知识缺口"
        subtitle="未覆盖问题沉淀，可生成草稿或忽略"
      />
      <Card>
        <Table
          loading={gapsQ.isLoading}
          rowKey="id"
          dataSource={gapsQ.data ?? []}
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
                    loading={promote.isPending && promote.variables?.id === g.id}
                    onClick={() => void promote.mutateAsync(g)}
                  >
                    生成草稿
                  </Button>
                  <Button
                    size="small"
                    icon={<StopOutlined />}
                    loading={dismiss.isPending && dismiss.variables === g.id}
                    onClick={() => void dismiss.mutateAsync(g.id)}
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
