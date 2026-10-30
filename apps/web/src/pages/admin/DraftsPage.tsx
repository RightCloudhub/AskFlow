import { ConfigurationWorkspace } from "../../components/admin/record-workspace";
import { useState } from "react";
import { Button, Drawer } from "antd";
import { useSearchParams } from "react-router-dom";
import type { ColumnsType } from "antd/es/table";
import { PageHeader, StatusBadge } from "../../components/admin";
import { DataTable, FilterBar, QueryFeedback, RefreshButton, WorkspacePanel } from "../../components/admin/workspace";
import { useRecordFilter } from "../../components/admin/use-record-filter";
import { useDrafts } from "../../hooks/use-knowledge";
import { DraftEditor } from "./draft-editor";
import { DraftReviewFlow } from "./draft-review-flow";
import type { Draft } from "../../api/types";

const SUMMARY_LENGTH = 80;
type DraftActions = { busy: boolean; open: (row: Draft) => void };

function draftColumns(actions: DraftActions): ColumnsType<Draft> {
  return [
    { title: "草稿", dataIndex: "title", render: (title, row) => <div className="af-record-title"><strong>{title}</strong>
      <small>{row.content.slice(0, SUMMARY_LENGTH)}{row.content.length > SUMMARY_LENGTH ? "…" : ""}</small></div> },
    { title: "状态", dataIndex: "status", render: (value) => <StatusBadge value={value} /> },
    { title: "审核", key: "actions", render: (_, row) => <Button size="small" disabled={actions.busy}
      onClick={() => actions.open(row)}>{row.status === "draft" ? "核对并审核" : "查看全文"}</Button> },
  ];
}

function useDraftSelection(rows: Draft[] | undefined) {
  const [params, setParams] = useSearchParams();
  const [busy, setBusy] = useState(false);
  const [selected, setSelected] = useState<string | null>(null);
  const selectedId = selected ?? params.get("draft_id");
  const actions: DraftActions = { busy, open: (row) => setSelected(row.id) };
  const current = rows?.find((row) => row.id === selectedId);
  function close() {
    if (busy) return;
    setSelected(null);
    setParams((previous) => { const next = new URLSearchParams(previous); next.delete("draft_id"); return next; }, { replace: true });
  }
  return { current, selectedId, busy, setBusy, actions, close };
}

function DraftReviewDrawer({ selection, query }: { selection: ReturnType<typeof useDraftSelection>; query: ReturnType<typeof useDrafts> }) {
  const { current, selectedId, busy, setBusy, close } = selection;
  return <Drawer title={current?.title ?? "草稿全文"} open={Boolean(selectedId)} onClose={close} closable={!busy}
    keyboard={!busy} mask={{ closable: !busy }} size="min(600px, 100vw)" destroyOnHidden>
    <QueryFeedback query={query} />
    {current ? <DraftReviewFlow key={JSON.stringify([current.id, current.title, current.content])}
      draft={current} onBusyChange={setBusy} onClose={close} /> :
      <p className="af-work-help">{query.isLoading ? "正在读取草稿…" : "未找到这份草稿，请重新加载或返回列表。"}</p>}
  </Drawer>;
}

export function DraftsPage() {
  const query = useDrafts();
  const selection = useDraftSelection(query.data);
  const filter = useRecordFilter({ rows: query.data ?? [], fields: ["title", "content"], statusField: "status" });
  return <div className="af-page"><PageHeader title="知识草稿" subtitle="核对答案再发布，让每一次知识补充有据可查。"
    actions={<RefreshButton query={query} />} />
    <ConfigurationWorkspace editor={<DraftEditor />}><WorkspacePanel title="草稿审核队列">
      <FilterBar {...filter} placeholder="搜索问题或答案" count={query.data ? filter.rows.length : undefined}
        options={[{ value: "all", label: "全部状态" }, { value: "draft", label: "待审核" },
          { value: "approved", label: "已通过" }, { value: "rejected", label: "已拒绝" }]} />
      <DataTable query={query} dataSource={filter.rows} columns={draftColumns(selection.actions)} emptyTitle={filter.filtered ? "没有匹配的草稿" : "还没有知识草稿"}
        emptyDescription="手动编写答案，或从知识缺口生成草稿后审核。" />
    </WorkspacePanel></ConfigurationWorkspace>
    <DraftReviewDrawer selection={selection} query={query} />
  </div>;
}
