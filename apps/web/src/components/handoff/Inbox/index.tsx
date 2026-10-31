import { useMemo, useState } from "react";
import { Input, Skeleton } from "antd";
import { SearchOutlined } from "@ant-design/icons";
import { formatWaiting, intentLabel } from "../../admin";
import { QueryFeedback, type QueryPresentation } from "../../admin/workspace";
import type { Handoff } from "../../../api/types";
import { HandoffStatus } from "../status";

type Props = {
  rows: Handoff[]; query: QueryPresentation; currentUserId?: string;
  selectedId?: string; disabled: boolean; onSelect: (row: Handoff) => void;
};
const VIEWS = [{ id: "queued", label: "待认领" }, { id: "mine", label: "我的会话" }, { id: "all", label: "全部" }];
const PLACEHOLDER_ROWS = 4;

function InboxRow({ row, props }: { row: Handoff; props: Props }) {
  const owner = row.claimed_by === props.currentUserId ? "我" : row.claimed_by_name || "其他座席";
  return <button type="button" className="af-inbox-row" aria-pressed={row.id === props.selectedId}
    disabled={props.disabled} onClick={() => props.onSelect(row)}>
    <span className="af-inbox-row-title"><strong>{row.user_name || "访客"}</strong>
      <span>{row.status === "queued" ? `等待 ${formatWaiting(row.created_at)}` : intentLabel(row.intent || "handoff")}</span></span>
    <span className="af-inbox-preview">{row.summary || "客户已请求人工协助，暂无转接摘要。"}</span>
    <span className="af-inbox-row-meta"><HandoffStatus status={row.status} />
      <span>{row.claimed_by ? owner : intentLabel(row.intent || "handoff")}</span></span>
  </button>;
}

export function HandoffInbox(props: Props) {
  const [view, setView] = useState("all");
  const [search, setSearch] = useState("");
  const matching = useMemo(() => props.rows.filter((row) =>
    [row.user_name, row.summary, row.conversation_id].some((value) => value?.toLocaleLowerCase().includes(search.trim().toLocaleLowerCase()))),
  [props.rows, search]);
  const groups: Record<string, Handoff[]> = { all: matching, queued: matching.filter((row) => row.status === "queued"),
    mine: matching.filter((row) => row.status === "claimed" && row.claimed_by === props.currentUserId) };
  const rows = groups[view];
  return <section className="af-inbox" aria-label="人工服务队列">
    <div className="af-inbox-tools"><h2>服务队列</h2>
      <div className="af-inbox-tabs" role="group" aria-label="会话范围">{VIEWS.map((item) =>
        <button type="button" key={item.id} aria-pressed={view === item.id} onClick={() => setView(item.id)}>
          {item.label}<span>{props.query.isLoading ? "—" : groups[item.id].length}</span></button>)}</div>
      <Input value={search} onChange={(event) => setSearch(event.target.value)} prefix={<SearchOutlined />} allowClear
        aria-label="搜索客户或会话" placeholder="搜索客户、摘要或会话编号" />
    </div>
    <QueryFeedback query={props.query} />
    <div className="af-inbox-list">{props.query.isLoading ? <Skeleton active={false} title={false} paragraph={{ rows: PLACEHOLDER_ROWS }} /> :
      rows.length ? rows.map((row) => <InboxRow key={row.id} row={row} props={props} />) :
        <div className="af-handoff-empty"><h3>{props.query.isError ? "服务队列暂不可用" : "暂无符合条件的会话"}</h3>
          <p>{search ? "试试客户姓名或其他关键词。" : "客户转人工后，会在这里等待认领。"}</p></div>}</div>
  </section>;
}
