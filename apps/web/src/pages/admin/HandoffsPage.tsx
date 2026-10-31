import { useEffect, useState } from "react";
import { ReloadOutlined } from "@ant-design/icons";
import { Button } from "antd";
import { HandoffInbox } from "../../components/handoff/Inbox";
import { SessionDetail } from "../../components/handoff/SessionDetail";
import { useHandoffs } from "../../hooks/use-ops";
import { useMe } from "../../hooks/use-auth";
import { QueryFeedback } from "../../components/admin/workspace";
import "../../styles/handoff-workspace.css";

export function HandoffsPage() {
  const query = useHandoffs();
  const me = useMe();
  const [selected, setSelected] = useState<string | null>(null);
  const [detailOpen, setDetailOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  useEffect(() => {
    if (!selected && query.data?.[0]) setSelected(query.data[0].id);
  }, [selected, query.data]);
  const current = query.data?.find((row) => row.id === selected) ?? (!selected ? query.data?.[0] : undefined);
  const waiting = query.data?.filter((row) => row.status === "queued").length;
  function setDraft(text: string) {
    if (current) setDrafts((previous) => ({ ...previous, [current.id]: text }));
  }
  return <div className="af-handoff" data-detail-open={detailOpen}>
    <header className="af-handoff-title"><div><h1>人工接管</h1>
      <p>{waiting == null ? "正在读取服务队列" : waiting ? `${waiting} 位客户等待认领` : "当前没有等待认领的客户"}</p></div>
      <div className="af-handoff-freshness"><span>{query.isError ? "队列同步暂不可用" : "队列自动更新"}</span>
        <Button icon={<ReloadOutlined />} loading={query.isFetching} onClick={() => void query.refetch()}>刷新队列</Button></div>
    </header>
    <QueryFeedback query={me} />
    <div className="af-handoff-grid">
      <HandoffInbox rows={query.data ?? []} query={query} currentUserId={me.data?.id}
        selectedId={current?.id} disabled={busy} onSelect={(row) => { setSelected(row.id); setDetailOpen(true); }} />
      <SessionDetail session={current ?? null} currentUser={me.data} busy={busy} onBusyChange={setBusy}
        draft={current ? drafts[current.id] ?? "" : ""} onDraftChange={setDraft}
        onBack={() => setDetailOpen(false)} />
    </div>
  </div>;
}
