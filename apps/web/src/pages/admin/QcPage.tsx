import { useEffect, useMemo, useState } from "react";
import { Card, Col, Empty, Row, Space, Spin, Table, Tag } from "antd";
import {
  DonutChart,
  PageHeader,
  StatCard,
  StatusBadge,
  type ChartDatum,
} from "../../components/admin";
import { api } from "../../api/client";

type Summary = {
  agent_runs?: number;
  refused_runs?: number;
  refuse_rate?: number;
  thumbs_up?: number;
  thumbs_down?: number;
  thumbs_down_rate?: number;
  handoffs?: number;
  messages?: number;
  quality_score_avg?: number | null;
};

type LowRun = {
  run_id: string;
  route: string;
  intent: string | null;
  refused: boolean;
  score: number;
  flags: string[];
};

const ROUTE_LABELS: Record<string, string> = {
  rag: "知识问答",
  tool: "工具调用",
  ticket: "建单",
  handoff: "转人工",
  clarify: "澄清",
  refuse: "拒答",
};

function scoreColor(score: number): string {
  if (score >= 80) return "success";
  if (score >= 50) return "warning";
  return "error";
}

export function QcPage() {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [runs, setRuns] = useState<LowRun[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    void (async () => {
      try {
        setSummary(await api<Summary>("/api/v1/admin/qc/summary"));
        const low = await api<{ runs: LowRun[] }>(
          "/api/v1/admin/qc/low-quality?limit=30"
        );
        setRuns(low.runs || []);
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const feedbackDonut: ChartDatum[] = useMemo(() => {
    if (!summary) return [];
    return [
      { key: "up", label: "好评", value: summary.thumbs_up ?? 0, color: "#52c41a" },
      { key: "down", label: "差评", value: summary.thumbs_down ?? 0, color: "#ff4d4f" },
    ];
  }, [summary]);

  const refuseDonut: ChartDatum[] = useMemo(() => {
    if (!summary) return [];
    const total = summary.agent_runs ?? 0;
    const refused = summary.refused_runs ?? 0;
    return [
      {
        key: "ok",
        label: "正常作答",
        value: Math.max(0, total - refused),
        color: "#1677ff",
      },
      { key: "refused", label: "拒答", value: refused, color: "#faad14" },
    ];
  }, [summary]);

  const columns = [
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
      title: "分数",
      dataIndex: "score",
      render: (s: number) => <Tag color={scoreColor(s)}>{s} 分</Tag>,
    },
    {
      title: "拒答",
      dataIndex: "refused",
      render: (v: boolean) => (v ? <Tag color="warning">是</Tag> : <Tag>否</Tag>),
    },
    {
      title: "Flags",
      dataIndex: "flags",
      render: (flags: string[]) => (
        <Space size={[4, 4]} wrap>
          {(flags || []).map((f) => (
            <StatusBadge key={f} value={f} label={f} />
          ))}
        </Space>
      ),
    },
  ];

  return (
    <div className="af-page">
      <PageHeader
        eyebrow="运营总览"
        title="质检中心"
        subtitle="基于拒答、弱证据 flags 与用户反馈的确定性评分（无二次 LLM）"
      />
      <Spin spinning={loading}>
        {summary ? (
          <>
            <Row gutter={[16, 16]}>
              <Col xs={24} sm={12} lg={6}>
                <StatCard
                  label="平均质检分"
                  value={summary.quality_score_avg}
                  tone="brand"
                />
              </Col>
              <Col xs={24} sm={12} lg={6}>
                <StatCard label="Agent 运行" value={summary.agent_runs} tone="info" />
              </Col>
              <Col xs={24} sm={12} lg={6}>
                <StatCard
                  label="拒答率"
                  value={summary.refuse_rate}
                  format="rate"
                  tone="warn"
                />
              </Col>
              <Col xs={24} sm={12} lg={6}>
                <StatCard
                  label="差评率"
                  value={summary.thumbs_down_rate}
                  format="rate"
                  tone="danger"
                />
              </Col>
            </Row>
            <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
              <Col xs={24} lg={12}>
                <Card title="作答 vs 拒答">
                  <DonutChart
                    data={refuseDonut}
                    centerLabel="运行"
                    centerValue={String(summary.agent_runs ?? 0)}
                  />
                </Card>
              </Col>
              <Col xs={24} lg={12}>
                <Card title="用户反馈">
                  <DonutChart
                    data={feedbackDonut}
                    centerLabel="反馈"
                    centerValue={String(
                      (summary.thumbs_up ?? 0) + (summary.thumbs_down ?? 0)
                    )}
                  />
                </Card>
              </Col>
            </Row>
          </>
        ) : !loading ? (
          <Empty description="暂无质检数据" />
        ) : null}

        <Card title="低分 / 拒答运行" style={{ marginTop: 16 }}>
          <Table
            size="middle"
            rowKey="run_id"
            dataSource={runs}
            columns={columns}
            pagination={{ pageSize: 10, showSizeChanger: false }}
            locale={{ emptyText: "暂无低分记录" }}
          />
        </Card>
      </Spin>
    </div>
  );
}
