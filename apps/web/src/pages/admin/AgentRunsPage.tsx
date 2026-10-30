import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Button, Descriptions, Drawer, Input, Timeline } from "antd";
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
  const [params, setParams] = useSearchParams();
  const initial = params.get("run_id") ?? "";
  const [lookup, setLookup] = useState(initial);
  const [selected, setSelected] = useState<string | null>(initial || null);
  const query = useAgentRuns();
  const detail = useAgentRunDetail(selected);
  const filter = useRecordFilter({ rows: query.data ?? [], fields: ["run_id", "intent", "route"] });
  useEffect(() => { setSelected(initial || null); setLookup(initial); }, [initial]);
  function open(id: string) {
    setSelected(id); setLookup(id);
    setParams((current) => { current.set("run_id", id); return current; }, { replace: true });
  }
  function close() {
    setSelected(null);
    setParams((current) => { current.delete("run_id"); return current; }, { replace: true });
  }
  return <div className="af-page"><PageHeader title="运行回放" subtitle="找到一次运行，核对处理步骤、证据与费用。"
    actions={<RefreshButton query={query} />} />
    <WorkspacePanel title="最近的运行"><form className="af-run-lookup" onSubmit={(event) => {
      event.preventDefault(); if (lookup.trim()) open(lookup.trim());
    }}><label className="af-field"><span>定位运行</span><Input value={lookup}
      onChange={(event) => setLookup(event.target.value)} placeholder="输入完整的运行编号" /></label>
      <Button type="primary" htmlType="submit" disabled={!lookup.trim()} loading={detail.isFetching && Boolean(selected)}>查询运行</Button>
    </form><FilterBar {...filter} placeholder="搜索运行编号、意图或路由" count={query.data ? filter.rows.length : undefined} />
      <DataTable query={query} rowKey="run_id" dataSource={filter.rows} columns={runColumns(open)}
        emptyTitle={filter.filtered ? "没有匹配的运行" : "尚无运行记录"} emptyDescription="客服对话产生运行后，可在这里回放执行过程。" />
    </WorkspacePanel><Drawer title="运行详情" open={Boolean(selected)} onClose={close} size="min(680px, 100vw)" destroyOnHidden>
      <QueryFeedback query={detail} /><RunDetailState query={detail} />
    </Drawer>
  </div>;
}
