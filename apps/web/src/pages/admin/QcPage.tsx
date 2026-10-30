import { Link } from "react-router-dom";
import type { ColumnsType } from "antd/es/table";
import { PageHeader, StatCard, DonutChart, StatusBadge } from "../../components/admin";
import { intentLabel } from "../../components/admin/labels";
import { BRAND } from "../../components/admin/theme";
import { DataTable, QueryFeedback, RefreshButton, WorkspacePanel } from "../../components/admin/workspace";
import { useQcLowQuality, useQcSummary } from "../../hooks/use-governance";
import { useFeatures } from "../../plugins/features";
import type { QcLowRun, QcSummary } from "../../api/types";

const GOOD_SCORE = 80;
const WARNING_SCORE = 50;
const ROUTES: Record<string, string> = { rag: "知识问答", tool: "工具调用", ticket: "创建工单", handoff: "转人工", clarify: "澄清", refuse: "拒答" };
function scoreTone(score: number) { return score >= GOOD_SCORE ? "good" : score >= WARNING_SCORE ? "warning" : "danger"; }

function qualityColumns(canReplay: boolean): ColumnsType<QcLowRun> {
  return [
    { title: "运行", dataIndex: "run_id", render: (value, row) => <div className="af-record-title">
      {canReplay ? <Link to={"/admin/agent-runs?run_id=" + encodeURIComponent(value)}>{value}</Link> : <strong>{value}</strong>}
      <small>{intentLabel(row.intent)} · {ROUTES[row.route] ?? row.route}</small></div> },
    { title: "质检分", dataIndex: "score", align: "right", render: (value) =>
      value == null ? "—" : <span className={"af-score af-score--" + scoreTone(value)}>{value} 分</span> },
    { title: "是否拒答", dataIndex: "refused", render: (value) => value ? "是" : "否" },
    { title: "质检标记", dataIndex: "flags", render: (flags: string[]) => <div className="af-work-tags">
      {flags?.length ? flags.map((flag) => <StatusBadge key={flag} value={flag} />) : "无"}</div> },
  ];
}

function QualityCharts({ summary }: { summary?: QcSummary }) {
  const total = summary?.agent_runs;
  const refused = summary?.refused_runs;
  const responses = total == null || refused == null ? [] : [
    { key: "answered", label: "正常作答", value: Math.max(0, total - refused), color: BRAND.accent },
    { key: "refused", label: "拒答", value: refused, color: BRAND.warning },
  ];
  const votes = [{ key: "up", label: "好评", value: summary?.thumbs_up, color: BRAND.accent },
    { key: "down", label: "差评", value: summary?.thumbs_down, color: BRAND.danger }];
  const feedback = votes.flatMap((row) => row.value == null ? [] : [{ ...row, value: row.value }]);
  return <div className="af-qc-charts">
    <WorkspacePanel title="作答与拒答"><DonutChart data={responses} centerLabel="模型运行" centerValue={total == null ? "—" : String(total)} /></WorkspacePanel>
    <WorkspacePanel title="客户反馈"><DonutChart data={feedback} /></WorkspacePanel>
  </div>;
}

export function QcPage() {
  const summary = useQcSummary();
  const runs = useQcLowQuality();
  const { enabled } = useFeatures();
  return <div className="af-page"><PageHeader title="质检中心" subtitle="先查看需要复核的回答，再结合拒答和客户反馈判断质量。"
    actions={<RefreshButton query={summary} />} /><QueryFeedback query={summary} />
    <div className="af-dashboard-metrics">
      <StatCard label="平均质检分" value={summary.data?.quality_score_avg} hint="规则评分，不额外调用模型" />
      <StatCard label="模型运行次数" value={summary.data?.agent_runs} />
      <StatCard label="拒答率" value={summary.data?.refuse_rate} format="rate" />
      <StatCard label="差评率" value={summary.data?.thumbs_down_rate} format="rate" />
    </div><div className="af-qc-workspace"><WorkspacePanel title="需要复核的运行" description="低分记录和拒答记录可作为补充知识、调整配置的依据。"
      actions={<RefreshButton query={runs} />}>
      <DataTable query={runs} rowKey="run_id" dataSource={runs.data ?? []} columns={qualityColumns(enabled("agent"))}
        emptyTitle="暂无需要复核的运行" emptyDescription="低分或拒答运行产生后，会显示在这里。" />
    </WorkspacePanel><QualityCharts summary={summary.data} /></div>
  </div>;
}
