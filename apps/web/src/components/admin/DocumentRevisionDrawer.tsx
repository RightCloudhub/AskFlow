import { useState } from "react";
import { Button, Descriptions, Drawer, List, Popconfirm, Select } from "antd";
import { useDocumentDiff, useDocumentGenerations, useRollbackDocument } from "../../hooks/use-documents";
import { StatusBadge } from "./StatusBadge";
import { EmptyState, QueryFeedback, WorkspacePanel } from "./workspace";
import { ActionFeedback, useActionFeedback } from "../common/action-feedback";
import type { DocumentRow, GenerationDiff } from "../../api/types";

type Props = { doc: DocumentRow | null; open: boolean; onClose: () => void };
const CHUNK_PREVIEW_LENGTH = 120;

function DiffChunks({ title, chunks }: { title: string; chunks: string[] }) {
  return <section className="af-work-stack"><h3 className="af-staff-heading">{title} · {chunks.length} 段</h3>
    {chunks.length ? chunks.map((chunk, index) => <details className="af-diff-chunk" key={index}>
      <summary>{chunk.slice(0, CHUNK_PREVIEW_LENGTH)}{chunk.length > CHUNK_PREVIEW_LENGTH ? "…" : ""}</summary>
      <p className="af-work-preview">{chunk}</p>
    </details>) : <p className="af-work-help">没有{title}。</p>}
  </section>;
}

function RevisionDiff({ data }: { data: GenerationDiff }) {
  return <WorkspacePanel title={"版本 " + data.from_generation + " → 版本 " + data.to_generation}
    description={"保持不变的知识分块：" + data.unchanged_count}>
    <div className="af-work-stack"><DiffChunks title="新增分块" chunks={data.added} /><DiffChunks title="删除分块" chunks={data.removed} /></div>
  </WorkspacePanel>;
}

type GenerationQuery = ReturnType<typeof useDocumentGenerations>;

function RevisionComparison({ docId, generations }: { docId: string; generations: number[] }) {
  const [from, setFrom] = useState<number>();
  const [to, setTo] = useState<number>();
  const start = from ?? generations[generations.length - 2] ?? null;
  const end = to ?? generations[generations.length - 1] ?? null;
  const query = useDocumentDiff(docId, start, end);
  const options = generations.map((value) => ({ value, label: "版本 " + value }));
  return <section className="af-work-stack"><div className="af-work-inline">
    <label className="af-field"><span>对比起始版本</span><Select aria-label="对比起始版本"
      value={start ?? undefined} options={options} onChange={setFrom} /></label>
    <label className="af-field"><span>对比目标版本</span><Select aria-label="对比目标版本"
      value={end ?? undefined} options={options} onChange={setTo} /></label>
  </div><QueryFeedback query={query} />
    {start === end ? <p className="af-work-help">请选择两个不同版本进行对比。</p> :
      query.isLoading ? <p className="af-work-help">正在对比知识分块…</p> : query.data && <RevisionDiff data={query.data} />}
  </section>;
}

function RevisionHistory({ docId, generations, query, current }: {
  docId: string; generations: number[]; query: GenerationQuery; current: number | undefined;
}) {
  const rollback = useRollbackDocument();
  const feedback = useActionFeedback();
  return <WorkspacePanel title="历史版本"><ActionFeedback state={feedback} />
    <List dataSource={[...generations].reverse()}
      locale={{ emptyText: query.isLoading ? "正在读取版本…" : query.isError ? "版本尚未加载，请重试。" : "尚无修订快照" }}
      renderItem={(generation) => <List.Item><span>版本 {generation}{generation === current ? " · 当前生效" : ""}</span>
        <Popconfirm title={"切换到版本 " + generation + "？"} description="该版本的知识分块将替换当前生效内容。"
          okText="确认回滚" cancelText="保留当前版本" onConfirm={() => feedback.run(async () => {
            await rollback.mutateAsync({ id: docId, generation }); await query.refetch();
          }, "文档已回滚到所选版本。") }>
          <Button size="small" disabled={generation === current || feedback.busy}>回滚到此版本</Button>
        </Popconfirm>
      </List.Item>} />
  </WorkspacePanel>;
}

function RevisionWorkspace({ doc }: { doc: DocumentRow }) {
  const query = useDocumentGenerations(doc.id);
  const generations = [...(query.data?.generations ?? [])].sort((a, b) => a - b);
  const current = query.data?.current_generation ?? doc.generation;
  return <div className="af-work-stack"><QueryFeedback query={query} /><Descriptions column={1} items={[
    { key: "current", label: "当前版本", children: current ?? "—" },
    { key: "count", label: "知识分块", children: doc.chunk_count },
    { key: "status", label: "索引状态", children: <StatusBadge value={doc.status} /> },
  ]} /><RevisionHistory docId={doc.id} generations={generations} query={query} current={current} />
    {generations.length > 1 ? <RevisionComparison docId={doc.id} generations={generations} /> :
      !query.isLoading && !query.isError && <EmptyState title="两个版本之间可以对比分块差异"
        description="文档产生下一份修订快照后，可查看新增与删除的内容。" />}
  </div>;
}

export function DocumentRevisionDrawer({ doc, open, onClose }: Props) {
  return <Drawer title={doc ? "版本 · " + (doc.title || doc.filename) : "文档版本"} open={open} onClose={onClose}
    size="min(600px, 100vw)" destroyOnHidden>
    {open && doc && <RevisionWorkspace key={doc.id} doc={doc} />}
  </Drawer>;
}
