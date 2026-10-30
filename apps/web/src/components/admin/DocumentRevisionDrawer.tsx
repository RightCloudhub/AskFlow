import { useRef, useState } from "react";
import { Button, Descriptions, Drawer, List } from "antd";
import { useDocumentGenerations } from "../../hooks/use-documents";
import { StatusBadge } from "./StatusBadge";
import { EmptyState, QueryFeedback, WorkspacePanel } from "./workspace";
import { RevisionComparison } from "./document-revision-parts";
import { DocumentRollbackFlow, type RollbackTarget } from "./document-rollback-flow";
import type { DocumentRow } from "../../api/types";

type Props = { doc: DocumentRow | null; open: boolean; onClose: () => void };
type GenerationQuery = ReturnType<typeof useDocumentGenerations>;

function RevisionHistory({ generations, query, current, onSelect }: {
  generations: number[]; query: GenerationQuery; current: number | undefined; onSelect: (target: RollbackTarget) => void;
}) {
  return <WorkspacePanel title="历史版本"><List dataSource={[...generations].reverse()}
    locale={{ emptyText: query.isLoading ? "正在读取版本…" : query.isError ? "版本尚未加载，请重试。" : "尚无修订快照" }}
    renderItem={(generation) => <List.Item><span>版本 {generation}{generation === current ? " · 当前生效" : ""}</span>
      <Button size="small" disabled={generation === current || current == null || query.isError || query.isFetching}
        onClick={() => { if (current != null) onSelect({ from: current, to: generation }); }}>核对并回滚</Button>
    </List.Item>} />
  </WorkspacePanel>;
}

function RevisionWorkspace({ doc, busy, onBusyChange }: { doc: DocumentRow; busy: boolean; onBusyChange: (value: boolean) => void }) {
  const query = useDocumentGenerations(doc.id);
  const [target, setTarget] = useState<RollbackTarget>();
  const history = useRef<HTMLDivElement>(null);
  const generations = [...(query.data?.generations ?? [])].sort((a, b) => a - b);
  const current = query.data?.current_generation ?? doc.generation;
  function exit() {
    if (busy) return;
    setTarget(undefined);
    requestAnimationFrame(() => history.current?.focus());
  }
  if (target) return <DocumentRollbackFlow doc={doc} target={target} generations={query}
    onBusyChange={onBusyChange} onExit={exit} />;
  return <div className="af-work-stack" ref={history} tabIndex={-1} role="group" aria-label="文档版本">
    <QueryFeedback query={query} /><Descriptions column={1} items={[
    { key: "current", label: "当前版本", children: current ?? "—" },
    { key: "count", label: "知识分块", children: doc.chunk_count },
    { key: "status", label: "索引状态", children: <StatusBadge value={doc.status} /> },
  ]} /><RevisionHistory generations={generations} query={query} current={current} onSelect={setTarget} />
    {generations.length > 1 ? <RevisionComparison docId={doc.id} generations={generations} /> :
      !query.isLoading && !query.isError && <EmptyState title="两个版本之间可以对比分块差异"
        description="文档产生下一份修订快照后，可查看新增与删除的内容。" />}
  </div>;
}

export function DocumentRevisionDrawer({ doc, open, onClose }: Props) {
  const [busy, setBusy] = useState(false);
  return <Drawer title={doc ? "版本 · " + (doc.title || doc.filename) : "文档版本"} open={open}
    onClose={() => { if (!busy) onClose(); }} closable={!busy} keyboard={!busy} mask={{ closable: !busy }}
    size="min(600px, 100vw)" destroyOnHidden>
    {open && doc && <RevisionWorkspace key={doc.id} doc={doc} busy={busy} onBusyChange={setBusy} />}
  </Drawer>;
}
