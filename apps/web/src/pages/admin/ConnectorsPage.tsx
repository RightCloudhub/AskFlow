import { useState } from "react";
import { Button, Card, Table, Tag } from "antd";
import { ApiOutlined } from "@ant-design/icons";
import { PageHeader } from "../../components/admin";
import { JsonView } from "../../components/common/json";
import {
  useConnectors,
  useInvokeConnector,
} from "../../hooks/use-governance";
import type { Connector } from "../../api/types";

export function ConnectorsPage() {
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const connectorsQ = useConnectors();
  const invoke = useInvokeConnector();

  async function onInvoke(name: string) {
    const r = await invoke.mutateAsync(name);
    setResult(r);
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
          loading={connectorsQ.isLoading}
          rowKey="name"
          dataSource={connectorsQ.data ?? []}
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
              render: (_: unknown, c: Connector) => (
                <Button
                  type="primary"
                  size="small"
                  icon={<ApiOutlined />}
                  loading={invoke.isPending && invoke.variables === c.name}
                  onClick={() => void onInvoke(c.name)}
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
