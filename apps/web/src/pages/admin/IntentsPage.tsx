import { useState } from "react";
import { Button, Select } from "antd";
import type { ColumnsType } from "antd/es/table";
import { PageHeader, StatusBadge } from "../../components/admin";
import { INTENT_LABELS, intentLabel } from "../../components/admin/labels";
import { DataTable, RefreshButton, SettingsSection, WorkspacePanel } from "../../components/admin/workspace";
import { ActionFeedback, useActionFeedback } from "../../components/common/action-feedback";
import { useIntents, useUpsertIntent } from "../../hooks/use-ops";
import type { IntentRow } from "../../api/types";

const DEFAULT_ROUTES: Record<string, string> = {
  faq: "rag", product: "rag", order_query: "tool", fault_report: "ticket", complaint: "ticket", handoff: "handoff",
};
const ROUTE_LABELS: Record<string, string> = { rag: "知识问答", tool: "工具调用", ticket: "创建工单", handoff: "转人工", clarify: "澄清问题" };
const COLUMNS: ColumnsType<IntentRow> = [
  { title: "客户意图", dataIndex: "intent", render: (value) => intentLabel(value) },
  { title: "处理方式", dataIndex: "route", render: (value) => ROUTE_LABELS[value] ?? value },
  { title: "状态", dataIndex: "enabled", render: (value) => <StatusBadge value={value ? "enabled" : "disabled"} /> },
  { title: "说明", dataIndex: "description" },
];

export function IntentsPage() {
  const query = useIntents();
  const mutation = useUpsertIntent();
  const feedback = useActionFeedback();
  const [intent, setIntent] = useState("faq");
  const [override, setOverride] = useState<string>();
  const current = query.data?.find((row) => row.intent === intent);
  const route = override ?? current?.route ?? DEFAULT_ROUTES[intent];
  async function save() {
    await feedback.run(() => mutation.mutateAsync({ intent, route }),
      "已保存：" + intentLabel(intent) + " → " + ROUTE_LABELS[route] + "。");
  }
  return <div className="af-page"><PageHeader title="意图路由" subtitle="决定不同客户问题进入知识问答、工具、工单或人工处理。"
    actions={<RefreshButton query={query} />} /><ActionFeedback state={feedback} />
    <div className="af-work-stack"><SettingsSection title="调整处理方式" description="选择意图后显示已有映射；保存后即时生效。">
      <div className="af-work-stack"><div className="af-work-inline">
        <label className="af-field"><span>客户意图</span><Select aria-label="客户意图" value={intent} disabled={feedback.busy}
          onChange={(value) => { setIntent(value); setOverride(undefined); feedback.clear(); }}
          options={Object.keys(DEFAULT_ROUTES).map((value) => ({ value, label: INTENT_LABELS[value] }))} /></label>
        <label className="af-field"><span>处理方式</span><Select aria-label="处理方式" value={route} disabled={feedback.busy}
          onChange={(value) => { setOverride(value); feedback.clear(); }} options={Object.entries(ROUTE_LABELS).map(([value, label]) => ({ value, label }))} /></label>
        <Button type="primary" loading={feedback.busy} disabled={query.isLoading || query.isError}
          onClick={() => void save()}>保存映射</Button></div>
        <p className="af-work-help">当前映射：{current ? ROUTE_LABELS[current.route] ?? current.route : query.isLoading ? "正在读取…" : "尚未配置，显示默认处理方式"}</p>
      </div>
    </SettingsSection><WorkspacePanel title="当前意图映射">
      <DataTable query={query} columns={COLUMNS} dataSource={query.data ?? []} pagination={false}
        emptyTitle="尚未配置运营映射" emptyDescription="选择意图并保存处理方式，即可建立映射记录。" />
    </WorkspacePanel></div>
  </div>;
}
