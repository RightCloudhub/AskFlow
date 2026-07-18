import { useEffect, useState } from "react";
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
import { api } from "../../api/client";
import { PageHeader } from "../../components/admin";
import { JsonView } from "../../components/common/json";

type RunRow = {
  run_id: string;
  route: string;
  intent: string | null;
  refused: boolean;
  flags: string[];
  steps: Array<{ kind: string; name: string; detail?: Record<string, unknown> }>;
  cost_summary: Record<string, unknown>;
  created_at?: string | null;
};

type RunDetail = RunRow & {
  cost?: {
    estimated_usd: number;
    entry_count: number;
    entries: Array<Record<string, unknown>>;
  };
};

const ROUTE_LABELS: Record<string, string> = {
  rag: "知识问答",
  tool: "工具调用",
  ticket: "建单",
  handoff: "转人工",
  clarify: "澄清",
  refuse: "拒答",
};

export function AgentRunsPage() {
  const [rows, setRows] = useState<RunRow[]>([]);
  const [detail, setDetail] = useState<RunDetail | null>(null);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);

  async function load() {
    setRows(await api<RunRow[]>("/api/v1/admin/agent-runs?limit=50"));
  }

  useEffect(() => {
    void load().finally(() => setLoading(false));
  }, []);

  async function openRun(runId: string) {
    const d = await api<RunDetail>(`/api/v1/admin/agent-runs/${runId}`);
    setDetail(d);
    setQuery(runId);
  }

  async function lookup() {
    if (!query.trim()) return;
    await openRun(query.trim());
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
            onPressEnter={() => void lookup()}
          />
          <Button type="primary" icon={<SearchOutlined />} onClick={() => void lookup()}>
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
            <Descriptions.Item label="意图">{detail.intent || "—"}</Descriptions.Item>
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
          loading={loading}
          rowKey="run_id"
          dataSource={rows}
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
              render: (s: RunRow["steps"]) => (s || []).length,
            },
            {
              title: "操作",
              key: "actions",
              width: 100,
              render: (_: unknown, r: RunRow) => (
                <Button
                  type="link"
                  size="small"
                  icon={<PlayCircleOutlined />}
                  onClick={() => void openRun(r.run_id)}
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
