import { useState } from "react";
import { Button, Form, Input } from "antd";
import { Link } from "react-router-dom";
import type { Draft, Gap } from "../../api/types";
import { gapReason } from "../../components/admin";
import { FlowFrame } from "../../components/common/FlowFrame";
import { GuidedForm } from "../../components/common/GuidedForm";
import { ActionFeedback, useActionFeedback } from "../../components/common/action-feedback";
import { usePromoteGap } from "../../hooks/use-knowledge";

const TITLES = ["核对问题", "补充答案", "核对提交", "操作结果"];
const TITLE_LIMIT = 120;
const EDITOR_ROWS = { minRows: 6, maxRows: 14 };
const REQUIRED = [{ required: true, whitespace: true, message: "请填写此项。" }];
type Props = { gap: Gap; onBusyChange: (busy: boolean) => void; onClose: () => void };

function GapContext({ gap }: { gap: Gap }) {
  const reason = gapReason(gap.reason);
  return <div className="af-form-review"><dl>
    <div><dt>客户原始问题</dt><dd>{gap.question}</dd></div>
    <div><dt>出现次数</dt><dd>{gap.hit_count}</dd></div>
    <div><dt>{reason.label}</dt><dd>{reason.hint}</dd></div>
  </dl></div>;
}

function DraftResult({ draft, onClose }: { draft: Draft; onClose: () => void }) {
  return <FlowFrame titles={TITLES} current={TITLES.length - 1} title="草稿已生成" onBack={() => undefined} backDisabled focusOnMount>
    <div className="af-flow-success"><p role="status">草稿已生成，请核对完整内容后审核。</p>
      <div className="af-form-review"><dl><div><dt>草稿标题</dt><dd>{draft.title}</dd></div>
        <div><dt>待审核答案</dt><dd>{draft.content}</dd></div></dl></div>
      <Link to={`/admin/drafts?draft_id=${encodeURIComponent(draft.id)}`}>前往审核这份草稿</Link>
    </div><div className="af-form-flow-actions"><Button onClick={onClose}>返回缺口列表</Button></div>
  </FlowFrame>;
}

export function GapDraftFlow({ gap, onBusyChange, onClose }: Props) {
  const [form] = Form.useForm();
  const promote = usePromoteGap();
  const feedback = useActionFeedback();
  const [draft, setDraft] = useState<Draft>();
  async function submit(values: Record<string, unknown>) {
    return feedback.run(async () => {
      const result = await promote.mutateAsync({ id: gap.id, title: String(values.title).trim(), content: String(values.content).trim() });
      setDraft(result);
    });
  }
  return <><div hidden={Boolean(draft)}><GuidedForm form={form} onFinish={submit} submitLabel="生成待审核草稿"
    onBusyChange={onBusyChange} active={!draft} disabled={Boolean(draft)}
    initialValues={{ title: gap.question.slice(0, TITLE_LIMIT) }} onValuesChange={feedback.clear}
    feedback={<ActionFeedback state={feedback} />} steps={[
      { title: TITLES[0], fields: [], content: <GapContext gap={gap} /> },
      { title: TITLES[1], fields: ["title", "content"], description: "根据可核实的资料补充答案，生成后仍需审核才能发布。", content: <>
        <Form.Item name="title" label="问题标题" rules={REQUIRED}><Input maxLength={TITLE_LIMIT} showCount /></Form.Item>
        <Form.Item name="content" label="待审核答案" rules={REQUIRED}>
          <Input.TextArea autoSize={EDITOR_ROWS} placeholder="填写适用条件、处理步骤与必要说明" />
        </Form.Item>
      </> },
    ]} review={(values) => <dl><div><dt>客户原始问题</dt><dd>{gap.question}</dd></div>
      <div><dt>问题标题</dt><dd>{String(values.title).trim()}</dd></div>
      <div><dt>待审核答案</dt><dd>{String(values.content).trim()}</dd></div></dl>} /></div>
    {draft && <DraftResult draft={draft} onClose={onClose} />}</>;
}
