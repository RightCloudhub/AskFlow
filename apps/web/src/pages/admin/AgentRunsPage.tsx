import { useState } from "react";
import {
  Button,
  Card,
  Descriptions,
  Input,
  Space,
  Table,
  Tag,
  Timeline,
} from "antd";
import { PlayCircleOutlined, SearchOutlined } from "@ant-design/icons";
import { PageHeader } from "../../components/admin";
import { JsonView } from "../../components/common/json";
import {
  useAgentRunDetail,
  useAgentRuns,
} from "../../hooks/use-governance";
import type { AgentRun } from "../../api/types";

const ROUTE_LABELS: Record<string, string> = {
  rag: "知识问答",
  tool: "工具调用",
  ticket: "建单",
  handoff: "转人工",
  clarify: "澄清",
  refuse: "拒答",
};

export function AgentRunsPage() {
  const [query, setQuery] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const runsQ = useAgentRuns();
  const detailQ = useAgentRunDetail(selectedId);
  const detail = detailQ.data;

  function openRun(runId: string) {
    setSelectedId(runId);
    setQuery(runId);
  }

  function lookup() {
    if (!query.trim()) return;
    openRun(query.trim());
  }

  return (
    <div className="af-page">
      <PageHeader
        eyebrow="运营总览"
        title="运行回放"
        subtitle="按 run_id 回放 Agent 步骤、flags 与费用"
      />
      <Card style={{ marginBottom: 16 }}>
        <Space.Compact style={{ width: "100%", maxWidth: 480 }}>
          <Input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="run_…"
            onPressEnter={lookup}
          />
          <Button
            type="primary"
            icon={<SearchOutlined />}
            loading={detailQ.isFetching && Boolean(selectedId)}
            onClick={lookup}
          >
            查询
          </Button>
        </Space.Compact>
      </Card>

      {detail ? (
        <Card title={`回放 · ${detail.run_id}`} style={{ marginBottom: 16 }}>
          <Descriptions size="small" column={2} style={{ marginBottom: 16 }}>
            <Descriptions.Item label="路由">
              {ROUTE_LABELS[detail.route] ?? detail.route}
            </Descriptions.Item>
            <Descriptions.Item label="意图">
              {detail.intent || "—"}
            </Descriptions.Item>
            <Descriptions.Item label="拒答">
              {detail.refused ? (
                <Tag color="warning">是</Tag>
              ) : (
                <Tag color="success">否</Tag>
              )}
            </Descriptions.Item>
          </Descriptions>
          <Timeline
            items={(detail.steps || []).map((s, i) => ({
              key: `${s.kind}-${s.name}-${i}`,
              children: (
                <div>
                  <strong>
                    [{s.kind}] {s.name}
                  </strong>
                  <JsonView data={s.detail || {}} compact initialExpandDepth={0} />
                </div>
              ),
            }))}
          />
          <JsonView data={detail.cost || detail.cost_summary} title="费用" />
        </Card>
      ) : null}

      <Card title="最近运行">
        <Table
          loading={runsQ.isLoading}
          rowKey="run_id"
          dataSource={runsQ.data ?? []}
          pagination={{ pageSize: 10 }}
          columns={[
            {
              title: "Run ID",
              dataIndex: "run_id",
              render: (id: string) => <code className="af-mono">{id}</code>,
            },
            {
              title: "路由",
              dataIndex: "route",
              render: (r: string) => ROUTE_LABELS[r] ?? r,
            },
            {
              title: "意图",
              dataIndex: "intent",
              render: (v: string | null) => v || "—",
            },
            {
              title: "步骤",
              dataIndex: "steps",
              width: 80,
              render: (s: AgentRun["steps"]) => (s || []).length,
            },
            {
              title: "操作",
              key: "actions",
              width: 100,
              render: (_: unknown, r: AgentRun) => (
                <Button
                  type="link"
                  size="small"
                  icon={<PlayCircleOutlined />}
                  onClick={() => openRun(r.run_id)}
                >
                  回放
                </Button>
              ),
            },
          ]}
          locale={{ emptyText: "暂无运行记录" }}
        />
      </Card>
    </div>
  );
}
