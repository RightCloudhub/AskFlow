import { useState } from "react";
import { Select } from "antd";
import { useDocumentDiff } from "../../hooks/use-documents";
import { QueryFeedback, WorkspacePanel } from "./workspace";
import type { GenerationDiff } from "../../api/types";

const CHUNK_PREVIEW_LENGTH = 120;

function DiffChunks({ title, chunks }: { title: string; chunks: string[] }) {
  return <section className="af-work-stack"><h3 className="af-staff-heading">{title} · {chunks.length} 段</h3>
    {chunks.length ? chunks.map((chunk, index) => <details className="af-diff-chunk" key={index}>
      <summary>{chunk.slice(0, CHUNK_PREVIEW_LENGTH)}{chunk.length > CHUNK_PREVIEW_LENGTH ? "…" : ""}</summary>
      <p className="af-work-preview">{chunk}</p>
    </details>) : <p className="af-work-help">没有{title}。</p>}
  </section>;
}

export function RevisionDiff({ data }: { data: GenerationDiff }) {
  return <WorkspacePanel title={"版本 " + data.from_generation + " → 版本 " + data.to_generation}
    description={"保持不变的知识分块：" + data.unchanged_count}>
    <div className="af-work-stack"><DiffChunks title="新增分块" chunks={data.added} /><DiffChunks title="删除分块" chunks={data.removed} /></div>
  </WorkspacePanel>;
}

export function RevisionComparison({ docId, generations }: { docId: string; generations: number[] }) {
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
