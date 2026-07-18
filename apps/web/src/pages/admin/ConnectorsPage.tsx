import { useEffect, useState } from "react";
import { Button, Card, Table, Tag } from "antd";
import { ApiOutlined } from "@ant-design/icons";
import { api } from "../../api/client";
import { PageHeader } from "../../components/admin";
import { JsonView } from "../../components/common/json";

type C = {
  name: string;
  base_url: string;
  enabled: boolean;
  description: string;
};

export function ConnectorsPage() {
  const [rows, setRows] = useState<C[]>([]);
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(true);
  const [invoking, setInvoking] = useState<string | null>(null);

  async function load() {
    setRows(await api<C[]>("/api/v1/admin/connectors"));
  }

  useEffect(() => {
    void load().finally(() => setLoading(false));
  }, []);

  async function invoke(name: string) {
    setInvoking(name);
    try {
      const r = await api<Record<string, unknown>>(
        `/api/v1/admin/connectors/${name}/invoke`,
        {
          method: "POST",
          body: JSON.stringify({ params: {} }),
        }
      );
      setResult(r);
    } finally {
      setInvoking(null);
    }
  }

  return (
    <div className="af-page">
      <PageHeader
        eyebrow="系统治理"
        title="业务连接器"
        subtitle="外部系统对接与试调用"
      />
      <Card title="连接器列表" style={{ marginBottom: 16 }}>
        <Table
          loading={loading}
          rowKey="name"
          dataSource={rows}
          pagination={false}
          columns={[
            { title: "名称", dataIndex: "name" },
            { title: "地址", dataIndex: "base_url" },
            {
              title: "状态",
              dataIndex: "enabled",
              width: 100,
              render: (e: boolean) =>
                e ? <Tag color="success">开启</Tag> : <Tag>关闭</Tag>,
            },
            { title: "说明", dataIndex: "description" },
            {
              title: "操作",
              key: "actions",
              width: 120,
              render: (_: unknown, c: C) => (
                <Button
                  type="primary"
                  size="small"
                  icon={<ApiOutlined />}
                  loading={invoking === c.name}
                  onClick={() => void invoke(c.name)}
                >
                  试调用
                </Button>
              ),
            },
          ]}
          locale={{ emptyText: "暂无连接器" }}
        />
      </Card>
      {result ? (
        <Card title="调用结果">
          <JsonView data={result} title="响应" />
        </Card>
      ) : null}
    </div>
  );
}
