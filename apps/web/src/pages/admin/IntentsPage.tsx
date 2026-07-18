import { useState } from "react";
import { Alert, Button, Card, Form, Select, Space, Table, Tag } from "antd";
import { SaveOutlined } from "@ant-design/icons";
import { PageHeader } from "../../components/admin";
import { useIntents, useUpsertIntent } from "../../hooks/use-ops";

const INTENTS = ["faq", "product", "order_query", "fault_report", "complaint", "handoff"];
const ROUTES = ["rag", "tool", "ticket", "handoff", "clarify"];

const INTENT_LABELS: Record<string, string> = {
  faq: "常见问题",
  product: "产品咨询",
  order_query: "订单查询",
  fault_report: "故障报修",
  complaint: "投诉",
  handoff: "转人工",
};

const ROUTE_LABELS: Record<string, string> = {
  rag: "知识问答",
  tool: "工具调用",
  ticket: "建单",
  handoff: "转人工",
  clarify: "澄清",
};

export function IntentsPage() {
  const [intent, setIntent] = useState("faq");
  const [route, setRoute] = useState("rag");
  const [msg, setMsg] = useState<string | null>(null);
  const intentsQ = useIntents();
  const upsert = useUpsertIntent();

  async function save() {
    await upsert.mutateAsync({ intent, route });
    setMsg(
      `已更新 ${INTENT_LABELS[intent] ?? intent} → ${ROUTE_LABELS[route] ?? route}`,
    );
  }

  return (
    <div className="af-page">
      <PageHeader
        eyebrow="智能配置"
        title="意图路由"
        subtitle="热更新意图 → 路由映射，无需重启服务"
      />
      {msg ? (
        <Alert type="success" showIcon message={msg} style={{ marginBottom: 16 }} />
      ) : null}

      <Card title="更新映射" style={{ marginBottom: 16 }}>
        <Space wrap>
          <Form.Item label="意图" style={{ marginBottom: 0 }}>
            <Select
              style={{ width: 180 }}
              value={intent}
              onChange={setIntent}
              options={INTENTS.map((i) => ({
                value: i,
                label: INTENT_LABELS[i] ?? i,
              }))}
            />
          </Form.Item>
          <Form.Item label="路由" style={{ marginBottom: 0 }}>
            <Select
              style={{ width: 180 }}
              value={route}
              onChange={setRoute}
              options={ROUTES.map((r) => ({
                value: r,
                label: ROUTE_LABELS[r] ?? r,
              }))}
            />
          </Form.Item>
          <Button
            type="primary"
            icon={<SaveOutlined />}
            loading={upsert.isPending}
            onClick={() => void save()}
          >
            保存
          </Button>
        </Space>
      </Card>

      <Card title="当前映射">
        <Table
          loading={intentsQ.isLoading}
          rowKey="id"
          dataSource={intentsQ.data ?? []}
          pagination={false}
          columns={[
            {
              title: "意图",
              dataIndex: "intent",
              render: (i: string) => INTENT_LABELS[i] ?? i,
            },
            {
              title: "路由",
              dataIndex: "route",
              render: (r: string) => (
                <Tag color="blue">{ROUTE_LABELS[r] ?? r}</Tag>
              ),
            },
            {
              title: "状态",
              dataIndex: "enabled",
              render: (e: boolean) =>
                e ? <Tag color="success">启用</Tag> : <Tag>禁用</Tag>,
            },
            { title: "说明", dataIndex: "description" },
          ]}
          locale={{ emptyText: "暂无意图配置" }}
        />
      </Card>
    </div>
  );
}
