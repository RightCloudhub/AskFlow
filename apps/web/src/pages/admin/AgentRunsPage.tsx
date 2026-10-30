import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Button, Descriptions, Input, Timeline } from "antd";
import type { ColumnsType } from "antd/es/table";
import { PageHeader } from "../../components/admin";
import { intentLabel } from "../../components/admin/labels";
import { DataTable, FilterBar, QueryFeedback, RefreshButton, WorkspacePanel, EmptyState } from "../../components/admin/workspace";
import { useRecordFilter } from "../../components/admin/use-record-filter";
import { JsonView } from "../../components/common/json";
import { useAgentRunDetail, useAgentRuns } from "../../hooks/use-governance";
import type { AgentRun, AgentRunDetail } from "../../api/types";

const ROUTES: Record<string, string> = { rag: "知识问答", tool: "工具调用", ticket: "创建工单", handoff: "转人工", clarify: "澄清", refuse: "拒答" };
function runColumns(open: (id: string) => void): ColumnsType<AgentRun> {
  return [
    { title: "运行编号", dataIndex: "run_id", render: (id) => <span className="af-record-secondary">{id}</span> },
    { title: "路由", dataIndex: "route", render: (value) => ROUTES[value] ?? value },
    { title: "意图", dataIndex: "intent", render: (value) => intentLabel(value) },
    { title: "步骤数", dataIndex: "steps", align: "right", render: (steps: AgentRun["steps"]) => steps?.length ?? 0 },
    { title: "操作", key: "open", render: (_, row) => <Button size="small" onClick={() => open(row.run_id)}>查看回放</Button> },
  ];
}
function RunDetail({ detail }: { detail: AgentRunDetail }) {
  return <div className="af-work-stack"><Descriptions column={{ xs: 1, sm: 2 }} items={[
    { key: "run", label: "运行编号", children: <span className="af-record-secondary">{detail.run_id}</span> },
    { key: "route", label: "路由", children: ROUTES[detail.route] ?? detail.route },
    { key: "intent", label: "意图", children: intentLabel(detail.intent) },
    { key: "refused", label: "拒答", children: detail.refused ? "是" : "否" },
  ]} /><Timeline items={(detail.steps ?? []).map((step, index) => ({
    key: String(index), children: <div className="af-work-stack"><div className="af-record-title"><strong>{step.name}</strong>
      <small>{step.kind}</small></div><JsonView data={step.detail ?? {}} compact initialExpandDepth={0} /></div>,
  }))} /><JsonView data={detail.cost ?? detail.cost_summary} title="调用费用" /></div>;
}

function RunDetailState({ query }: { query: ReturnType<typeof useAgentRunDetail> }) {
  if (query.isLoading) return <p className="af-work-help">正在读取运行步骤…</p>;
  if (query.data) return <RunDetail detail={query.data} />;
  if (query.isError) return null;
  return <EmptyState title="没有找到这次运行" description="请核对运行编号。" />;
}

export function AgentRunsPage() {
  const [params] = useSearchParams();
  const initial = params.get("run_id") ?? "";
  const [lookup, setLookup] = useState(initial);
  const [selected, setSelected] = useState<string | null>(initial || null);
  const query = useAgentRuns();
  const detail = useAgentRunDetail(selected);
  const filter = useRecordFilter({ rows: query.data ?? [], fields: ["run_id", "intent", "route"] });
  function open(id: string) { setSelected(id); setLookup(id); }
  return <div className="af-page"><PageHeader title="运行回放" subtitle="沿着一次运行的步骤，核对路由、证据和调用费用。"
    actions={<RefreshButton query={query} />} /><div className="af-work-stack">
    <WorkspacePanel title="定位一次运行"><form className="af-work-inline" onSubmit={(event) => { event.preventDefault(); if (lookup.trim()) open(lookup.trim()); }}>
      <label className="af-field"><span>运行编号</span><Input value={lookup} onChange={(event) => setLookup(event.target.value)} placeholder="输入完整的 run_id" /></label>
      <Button type="primary" htmlType="submit" disabled={!lookup.trim()} loading={detail.isFetching && Boolean(selected)}>查询运行</Button>
    </form></WorkspacePanel>
    {selected && <WorkspacePanel title="运行详情" actions={<Button onClick={() => setSelected(null)}>关闭详情</Button>}>
      <QueryFeedback query={detail} /><RunDetailState query={detail} />
    </WorkspacePanel>}
    <WorkspacePanel title="最近的运行"><FilterBar {...filter} placeholder="搜索运行编号、意图或路由" count={query.data ? filter.rows.length : undefined} />
      <DataTable query={query} rowKey="run_id" dataSource={filter.rows} columns={runColumns(open)}
        emptyTitle={filter.filtered ? "没有匹配的运行" : "尚无运行记录"} emptyDescription="客服对话产生运行后，可在这里回放执行过程。" />
    </WorkspacePanel></div>
  </div>;
}
