import { useEffect } from "react";
import { Form, Select } from "antd";
import { INTENT_LABELS, intentLabel } from "../../components/admin/labels";
import { QueryFeedback, SettingsSection } from "../../components/admin/workspace";
import { GuidedForm } from "../../components/common/GuidedForm";
import { ActionFeedback, useActionFeedback } from "../../components/common/action-feedback";
import { useIntents, useUpsertIntent } from "../../hooks/use-ops";

const DEFAULT_ROUTES: Record<string, string> = {
  faq: "rag", product: "rag", order_query: "tool", fault_report: "ticket", complaint: "ticket", handoff: "handoff",
};
export const ROUTE_LABELS: Record<string, string> = { rag: "知识问答", tool: "工具调用", ticket: "创建工单", handoff: "转人工", clarify: "澄清问题" };
const REQUIRED = [{ required: true, message: "请选择此项。" }];

export function IntentEditor() {
  const [form] = Form.useForm();
  const query = useIntents();
  const mutation = useUpsertIntent();
  const feedback = useActionFeedback();
  const intent = Form.useWatch("intent", form) ?? "faq";
  const previous = query.data?.find((row) => row.intent === intent)?.route ?? DEFAULT_ROUTES[intent];
  useEffect(() => {
    if (!form.isFieldTouched("route")) form.setFields([{ name: "route", value: previous, touched: false }]);
  }, [form, previous]);
  function selectIntent(value: string) {
    const route = query.data?.find((row) => row.intent === value)?.route ?? DEFAULT_ROUTES[value];
    form.setFields([{ name: "route", value: route, touched: false, errors: [] }]);
  }
  async function save(values: Record<string, unknown>) {
    return feedback.run(() => mutation.mutateAsync({ intent: String(values.intent), route: String(values.route) }), "意图映射已保存并生效。");
  }
  return <SettingsSection title="调整处理方式" description="选择客户意图，核对处理方式与生效范围后保存。">
    <QueryFeedback query={query} /><GuidedForm form={form} initialValues={{ intent: "faq", route: "rag" }}
      onFinish={save} submitLabel="保存并生效" disabled={query.isLoading || query.isError}
      onValuesChange={feedback.clear} feedback={<ActionFeedback state={feedback} />} steps={[
        { title: "选择客户意图", fields: ["intent"], content: <Form.Item name="intent" label="客户意图" rules={REQUIRED}>
          <Select onChange={selectIntent} options={Object.keys(DEFAULT_ROUTES).map((value) => ({ value, label: INTENT_LABELS[value] }))} />
        </Form.Item> },
        { title: "选择处理方式", fields: ["route"], content: <><p className="af-work-help">当前处理方式：{ROUTE_LABELS[previous] ?? previous}</p>
          <Form.Item name="route" label="保存后的处理方式" rules={REQUIRED}>
            <Select options={Object.entries(ROUTE_LABELS).map(([value, label]) => ({ value, label }))} />
          </Form.Item></> },
      ]} review={(values) => <dl><div><dt>客户意图</dt><dd>{intentLabel(String(values.intent))}</dd></div>
        <div><dt>处理方式</dt><dd>{ROUTE_LABELS[String(values.route)]}</dd></div>
        <div><dt>生效范围</dt><dd>保存后启用此映射，用于后续客户问题的处理。</dd></div></dl>} />
  </SettingsSection>;
}
