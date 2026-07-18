import { Card, Collapse, Table, Tag } from "antd";
import { PageHeader } from "../../components/admin";
import { JsonView } from "../../components/common/json";
import { useAuditLogs } from "../../hooks/use-governance";
import type { AuditLog } from "../../api/types";

export function AuditPage() {
  const auditQ = useAuditLogs();

  return (
    <div className="af-page">
      <PageHeader
        eyebrow="系统治理"
        title="审计日志"
        subtitle="关键操作留痕，支持合规追溯"
      />
      <Card>
        <Table
          loading={auditQ.isLoading}
          rowKey="id"
          dataSource={auditQ.data ?? []}
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
              render: (_: unknown, a: AuditLog) =>
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
              render: (_: unknown, a: AuditLog) => (
                <Collapse
                  ghost
                  size="small"
                  items={[
                    {
                      key: "1",
                      label: "查看 JSON",
                      children: (
                        <JsonView
                          data={a.detail}
                          compact
                          initialExpandDepth={1}
                        />
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
