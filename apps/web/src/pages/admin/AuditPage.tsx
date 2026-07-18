import { useEffect, useState } from "react";
import { Card, Collapse, Table, Tag } from "antd";
import { api } from "../../api/client";
import { PageHeader } from "../../components/admin";
import { JsonView } from "../../components/common/json";

type Audit = {
  id: string;
  action: string;
  resource_type: string;
  resource_id: string | null;
  detail: Record<string, unknown>;
  created_at: string;
};

export function AuditPage() {
  const [rows, setRows] = useState<Audit[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    void api<Audit[]>("/api/v1/admin/audit-logs")
      .then(setRows)
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="af-page">
      <PageHeader
        eyebrow="系统治理"
        title="审计日志"
        subtitle="关键操作留痕，支持合规追溯"
      />
      <Card>
        <Table
          loading={loading}
          rowKey="id"
          dataSource={rows}
          pagination={{ pageSize: 15 }}
          columns={[
            {
              title: "动作",
              dataIndex: "action",
              render: (a: string) => <Tag color="geekblue">{a}</Tag>,
            },
            {
              title: "资源",
              key: "resource",
              render: (_: unknown, a: Audit) =>
                `${a.resource_type} ${a.resource_id || ""}`.trim(),
            },
            {
              title: "时间",
              dataIndex: "created_at",
              width: 200,
            },
            {
              title: "详情",
              key: "detail",
              render: (_: unknown, a: Audit) => (
                <Collapse
                  ghost
                  size="small"
                  items={[
                    {
                      key: "1",
                      label: "查看 JSON",
                      children: (
                        <JsonView data={a.detail} compact initialExpandDepth={1} />
                      ),
                    },
                  ]}
                />
              ),
            },
          ]}
          locale={{ emptyText: "暂无审计记录" }}
        />
      </Card>
    </div>
  );
}
