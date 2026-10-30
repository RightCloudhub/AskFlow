import { useEffect, useState } from "react";
import { Button, Radio } from "antd";
import { Link } from "react-router-dom";
import type { Draft } from "../../api/types";
import { StatusBadge } from "../../components/admin";
import { FlowFrame } from "../../components/common/FlowFrame";
import { ActionFeedback, useActionFeedback } from "../../components/common/action-feedback";
import { useApproveDraft, useRejectDraft } from "../../hooks/use-knowledge";

const TITLES = ["核对全文", "审核决定", "提交结果"];
type Decision = "approve" | "reject";
type Props = { draft: Draft; onBusyChange: (busy: boolean) => void; onClose: () => void };
const DECISIONS = {
  approve: { label: "通过并发布", consequence: "答案将发布到知识库，用于客服回答。", result: "草稿已通过并发布。" },
  reject: { label: "拒绝草稿", consequence: "草稿将标记为已拒绝，保留记录，不发布到知识库。", result: "草稿已拒绝，记录已保留。" },
};

function DraftContent({ draft }: { draft: Draft }) {
  return <div className="af-form-review"><dl>
    <div><dt>客户问题</dt><dd>{draft.title}</dd></div>
    <div><dt>完整答案</dt><dd>{draft.content}</dd></div>
  </dl></div>;
}

function useDraftReview({ draft, onBusyChange }: Props) {
  const approve = useApproveDraft();
  const reject = useRejectDraft();
  const feedback = useActionFeedback();
  const [current, setCurrent] = useState(0);
  const [decision, setDecision] = useState<Decision>();
  const [result, setResult] = useState<Decision>();
  useEffect(() => { onBusyChange(feedback.busy); }, [feedback.busy, onBusyChange]);
  async function submit() {
    if (!decision || result || draft.status !== "draft") return;
    const mutation = decision === "approve" ? approve : reject;
    const done = await feedback.run(() => mutation.mutateAsync(draft.id));
    if (done) { setResult(decision); setCurrent(TITLES.length - 1); }
  }
  function back(index: number) {
    if (feedback.busy || result || index >= current) return;
    setCurrent(index); feedback.clear();
  }
  return { current, setCurrent, decision, setDecision, result, feedback, submit, back };
}

type ReviewState = ReturnType<typeof useDraftReview>;

function ReviewDecision({ draft, state }: { draft: Draft; state: ReviewState }) {
  return <div className="af-work-stack"><DraftContent draft={draft} />
    <Radio.Group aria-label="审核决定" value={state.decision} disabled={state.feedback.busy} onChange={(event) => {
      state.setDecision(event.target.value); state.feedback.clear();
    }} options={Object.entries(DECISIONS).map(([value, option]) => ({ value, label: option.label }))} />
    <p className="af-work-help">{state.decision ? DECISIONS[state.decision].consequence : "请选择审核结果，确认后提交。"}</p>
  </div>;
}

function ReviewActions({ state, onClose }: { state: ReviewState; onClose: () => void }) {
  const { current, result, decision, feedback } = state;
  if (result) return <div className="af-form-flow-actions"><Button onClick={onClose}>返回列表</Button></div>;
  return <div className="af-form-flow-actions">
    {current > 0 && <Button disabled={feedback.busy} onClick={() => state.back(current - 1)}>上一步</Button>}
    {current === 0 ? <Button type="primary" onClick={() => state.setCurrent(1)}>下一步</Button> :
      <Button type="primary" danger={decision === "reject"} disabled={!decision} loading={feedback.busy}
        onClick={() => void state.submit()}>{decision ? DECISIONS[decision].label : "提交审核结果"}</Button>}
  </div>;
}

export function DraftReviewFlow(props: Props) {
  const { draft, onClose } = props;
  const state = useDraftReview(props);
  const { current, result, feedback } = state;
  if (draft.status !== "draft" && !result) return <div className="af-work-stack">
    <StatusBadge value={draft.status} /><DraftContent draft={draft} />
    <p className="af-work-help">这份草稿已完成审核。</p><Button onClick={onClose}>返回列表</Button>
  </div>;
  return <FlowFrame titles={TITLES} current={current} onBack={state.back} busy={feedback.busy} backDisabled={Boolean(result)} focusOnMount>
    {current === 0 && <DraftContent draft={draft} />}
    {current === 1 && <ReviewDecision draft={draft} state={state} />}
    {result && <div className="af-flow-success"><p role="status">{DECISIONS[result].result}</p>
      {result === "approve" && <Link to="/admin/documents">查看知识文档</Link>}
    </div>}
    <ActionFeedback state={feedback} /><ReviewActions state={state} onClose={onClose} />
  </FlowFrame>;
}
