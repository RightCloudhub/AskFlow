import { useEffect, useState } from "react";
import { Button } from "antd";
import type { DocumentRow } from "../../api/types";
import { useDocumentDiff, useDocumentGenerations, useRollbackDocument } from "../../hooks/use-documents";
import { FlowFrame } from "../common/FlowFrame";
import { ActionFeedback, useActionFeedback } from "../common/action-feedback";
import { QueryFeedback } from "./workspace";
import { RevisionDiff } from "./document-revision-parts";

const TITLES = ["核对差异", "确认回滚", "回滚结果"];
export type RollbackTarget = { from: number; to: number };
type Props = {
  doc: DocumentRow; target: RollbackTarget; generations: ReturnType<typeof useDocumentGenerations>;
  onExit: () => void; onBusyChange: (busy: boolean) => void;
};

function useRollbackFlow({ doc, target, generations, onBusyChange }: Props) {
  const [current, setCurrent] = useState(0);
  const [result, setResult] = useState<DocumentRow>();
  const diff = useDocumentDiff(doc.id, target.from, target.to);
  const rollback = useRollbackDocument();
  const feedback = useActionFeedback();
  const changed = generations.data?.current_generation !== target.from;
  const ready = Boolean(diff.data) && !diff.isFetching && !diff.isError && !generations.isError && !changed;
  useEffect(() => { onBusyChange(feedback.busy); }, [feedback.busy, onBusyChange]);
  async function submit() {
    if (!ready || result) return;
    await feedback.run(async () => {
      const latest = await generations.refetch();
      if (latest.isError || !latest.data) throw new Error("无法确认当前文档版本，请重新加载后再试。");
      if (latest.data.current_generation !== target.from || !latest.data.generations.includes(target.to)) {
        throw new Error("文档版本已变更，请返回版本列表重新核对。");
      }
      const saved = await rollback.mutateAsync({ id: doc.id, generation: target.to });
      setResult(saved); setCurrent(TITLES.length - 1);
    });
  }
  function back(index: number) {
    if (feedback.busy || result || index >= current) return;
    setCurrent(index); feedback.clear();
  }
  return { current, setCurrent, result, diff, feedback, changed, ready, submit, back };
}

function RollbackSummary({ doc, target }: Pick<Props, "doc" | "target">) {
  return <div className="af-form-review"><dl>
    <div><dt>知识文档</dt><dd>{doc.title || doc.filename}</dd></div>
    <div><dt>当前生效版本</dt><dd>版本 {target.from}</dd></div>
    <div><dt>回滚目标</dt><dd>版本 {target.to}</dd></div>
  </dl></div>;
}

type RollbackState = ReturnType<typeof useRollbackFlow>;

function RollbackContent({ state, ...props }: Props & { state: RollbackState }) {
  const { current, result, diff } = state;
  if (result) return <div className="af-flow-success"><p role="status">文档版本已切换。</p>
    <div className="af-form-review"><dl><div><dt>当前生效版本</dt><dd>{result.generation ?? "—"}</dd></div>
      <div><dt>知识分块</dt><dd>{result.chunk_count}</dd></div></dl></div>
  </div>;
  return <div className="af-work-stack"><RollbackSummary doc={props.doc} target={props.target} />
    <QueryFeedback query={props.generations} /><QueryFeedback query={diff} />
    {state.changed && <p role="status" className="af-work-help">当前版本已变化，请返回版本列表重新选择。</p>}
    {current === 0 && <>{diff.isLoading && <p className="af-work-help">正在读取这次回滚的分块差异…</p>}
      {diff.data && <RevisionDiff data={diff.data} />}</>}
    {current === 1 && <p className="af-work-help">确认后，版本 {props.target.to} 的知识分块将替换当前生效内容，用于后续客服检索。</p>}
  </div>;
}

function RollbackActions({ state, onExit }: { state: RollbackState; onExit: () => void }) {
  const { current, result, feedback } = state;
  return <div className="af-form-flow-actions">
    <Button disabled={feedback.busy} onClick={onExit}>返回版本列表</Button>
    {!result && <>{current > 0 && <Button disabled={feedback.busy} onClick={() => state.back(current - 1)}>上一步</Button>}
      {current === 0 ? <Button type="primary" disabled={!state.ready} onClick={() => state.setCurrent(1)}>下一步</Button> :
        <Button type="primary" disabled={!state.ready} loading={feedback.busy} onClick={() => void state.submit()}>确认回滚</Button>}
    </>}
  </div>;
}

export function DocumentRollbackFlow(props: Props) {
  const state = useRollbackFlow(props);
  return <FlowFrame titles={TITLES} current={state.current} busy={state.feedback.busy} onBack={state.back}
    backDisabled={Boolean(state.result)} focusOnMount>
    <RollbackContent {...props} state={state} /><ActionFeedback state={state.feedback} />
    <RollbackActions state={state} onExit={props.onExit} />
  </FlowFrame>;
}
