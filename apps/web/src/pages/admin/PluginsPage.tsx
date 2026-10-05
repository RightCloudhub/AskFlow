import { Alert, Card, Col, Row, Space, Table, Tag, Typography } from "antd";
import { AppstoreOutlined } from "@ant-design/icons";
import { PageHeader, StatCard } from "../../components/admin";
import { useFeaturesDiscovery } from "../../hooks/use-governance";
import type { PluginCatalogItem } from "../../plugins/types";

const { Text, Paragraph } = Typography;

/** Display labels for known plugin ids (fallback: id itself). */
const PLUGIN_LABELS: Record<string, string> = {
  core: "核心",
  rag: "检索增强",
  agent: "Agent 管线",
  tools: "工具",
  ticket: "工单",
  handoff: "人工接管",
  knowledge: "知识闭环",
  ops: "运营配置",
  cost: "成本",
  sla: "SLA",
  notify: "通知",
  sso: "单点登录",
  teams: "技能组",
  connectors: "业务连接器",
  launch: "上线卡片",
  analytics: "运营看板",
  mcp: "MCP",
  widget: "嵌入组件",
  feishu: "飞书",
  wecom: "企微",
  dingtalk: "钉钉",
  qc: "质检",
};

function pluginLabel(id: string): string {
  return PLUGIN_LABELS[id] ?? id;
}

export function PluginsPage() {
  const q = useFeaturesDiscovery();
  const data = q.data;
  const plugins = data?.plugins ?? [];
  const enabledCount = plugins.filter((p) => p.enabled).length;
  const loadedCount = plugins.filter((p) => p.loaded).length;

  return (
    <div className="af-page">
      <PageHeader
        eyebrow="系统治理"
        title="插件与能力"
        subtitle="查看当前 Profile、已加载插件与扩展点（启动期装配，运行时只读）"
      />

      <Alert
        type="info"
        showIcon
        style={{ marginBottom: 16 }}
        message="配置方式"
        description={
          <Paragraph style={{ marginBottom: 0 }}>
            通过环境变量 <Text code>ASKFLOW_PROFILE</Text>（如{" "}
            <Text code>full</Text> / <Text code>mvp</Text> /{" "}
            <Text code>core-only</Text>）与可选增量{" "}
            <Text code>ASKFLOW_FEATURES=+sla,-mcp</Text> 控制能力组合；修改后需重启
            API。前端导航与路由会随已启用 features 自动收敛。
          </Paragraph>
        }
      />

      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={24} sm={12} md={6}>
          <StatCard
            label="当前 Profile"
            value={data?.profile ?? "—"}
            format="raw"
            prefix={<AppstoreOutlined />}
          />
        </Col>
        <Col xs={24} sm={12} md={6}>
          <StatCard
            label="已启用"
            value={enabledCount}
            hint={`/ ${plugins.length}`}
          />
        </Col>
        <Col xs={24} sm={12} md={6}>
          <StatCard label="已加载" value={loadedCount} />
        </Col>
        <Col xs={24} sm={12} md={6}>
          <StatCard
            label="路由处理器"
            value={data?.route_handlers?.length ?? 0}
          />
        </Col>
      </Row>

      <Card title="Profile 与增量" style={{ marginBottom: 16 }} loading={q.isLoading}>
        <Space wrap size={[8, 8]}>
          <Text type="secondary">可用 Profile：</Text>
          {(data?.profiles ?? []).map((p) => (
            <Tag key={p} color={p === data?.profile ? "blue" : "default"}>
              {p}
            </Tag>
          ))}
          {data?.feature_deltas ? (
            <>
              <Text type="secondary">ASKFLOW_FEATURES：</Text>
              <Tag color="purple">{data.feature_deltas}</Tag>
            </>
          ) : (
            <Text type="secondary">无 feature 增量</Text>
          )}
        </Space>
      </Card>

      <Card title="插件目录" style={{ marginBottom: 16 }}>
        <Table<PluginCatalogItem>
          loading={q.isLoading}
          rowKey="id"
          dataSource={plugins}
          pagination={false}
          size="middle"
          columns={[
            {
              title: "插件",
              dataIndex: "id",
              render: (id: string) => (
                <Space>
                  <Text strong>{pluginLabel(id)}</Text>
                  <Text type="secondary" code>
                    {id}
                  </Text>
                </Space>
              ),
            },
            {
              title: "依赖",
              dataIndex: "depends",
              render: (deps: string[]) =>
                deps.length ? (
                  <Space size={[4, 4]} wrap>
                    {deps.map((d) => (
                      <Tag key={d}>{d}</Tag>
                    ))}
                  </Space>
                ) : (
                  <Text type="secondary">—</Text>
                ),
            },
            {
              title: "启用",
              dataIndex: "enabled",
              width: 100,
              render: (v: boolean) =>
                v ? <Tag color="success">是</Tag> : <Tag>否</Tag>,
            },
            {
              title: "已加载",
              dataIndex: "loaded",
              width: 100,
              render: (v: boolean) =>
                v ? <Tag color="processing">是</Tag> : <Tag>否</Tag>,
            },
          ]}
          locale={{ emptyText: "暂无插件元数据" }}
        />
      </Card>

      <Row gutter={[16, 16]}>
        <Col xs={24} lg={12}>
          <Card title="Pipeline 路由" loading={q.isLoading}>
            <Space wrap>
              {(data?.route_handlers ?? []).map((r) => (
                <Tag key={r} color="cyan">
                  {r}
                </Tag>
              ))}
              {!data?.route_handlers?.length ? (
                <Text type="secondary">无</Text>
              ) : null}
            </Space>
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card title="Side effects" loading={q.isLoading}>
            <Space wrap>
              {(data?.side_effects ?? []).map((s) => (
                <Tag key={s} color="geekblue">
                  {s}
                </Tag>
              ))}
              {!data?.side_effects?.length ? (
                <Text type="secondary">无</Text>
              ) : null}
            </Space>
          </Card>
        </Col>
        <Col span={24}>
          <Card title="后端注册的 Admin 导航" loading={q.isLoading}>
            <Table
              rowKey={(r) => `${r.plugin_id}-${r.to}`}
              dataSource={data?.admin_nav ?? []}
              pagination={false}
              size="small"
              columns={[
                { title: "插件", dataIndex: "plugin_id", width: 120 },
                { title: "路径", dataIndex: "to" },
                { title: "标签", dataIndex: "label", width: 120 },
                { title: "排序", dataIndex: "order", width: 80 },
              ]}
              locale={{ emptyText: "无" }}
            />
          </Card>
        </Col>
      </Row>
    </div>
  );
}
