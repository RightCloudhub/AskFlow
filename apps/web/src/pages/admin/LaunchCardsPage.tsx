import { useState } from "react";
import { Button, Input } from "antd";
import type { ColumnsType } from "antd/es/table";
import { PageHeader, StatusBadge, formatRate } from "../../components/admin";
import { DataTable, FilterBar, RefreshButton, SettingsSection, WorkspacePanel } from "../../components/admin/workspace";
import { useRecordFilter } from "../../components/admin/use-record-filter";
import { ActionFeedback, useActionFeedback } from "../../components/common/action-feedback";
import { useCreateLaunchCard, useLaunchCards } from "../../hooks/use-governance";
import type { LaunchCard } from "../../api/types";

function rate(value?: number) { return value == null ? "尚未记录" : formatRate(value); }
const COLUMNS: ColumnsType<LaunchCard> = [
  { title: "变更", dataIndex: "title" },
  { title: "阶段", dataIndex: "status", render: (value) => <StatusBadge value={value} /> },
  { title: "预期 FAQ 解决率", key: "expected", align: "right", render: (_, row) => rate(row.expected_metrics?.faq_resolve_rate) },
  { title: "实测 FAQ 解决率", key: "measured", align: "right", render: (_, row) => rate(row.measured_metrics?.faq_resolve_rate) },
];

export function LaunchCardsPage() {
  const query = useLaunchCards();
  const create = useCreateLaunchCard();
  const feedback = useActionFeedback();
  const [title, setTitle] = useState("");
  const filter = useRecordFilter({ rows: query.data ?? [], fields: ["title"], statusField: "status" });
  async function submit() {
    if (!title.trim()) return;
    const done = await feedback.run(() => create.mutateAsync(title.trim()), "上线卡片已创建。");
    if (done) setTitle("");
  }
  return <div className="af-page"><PageHeader title="上线卡片" subtitle="将变更目标与实测指标放在一起，跟踪发布后的效果。"
    actions={<RefreshButton query={query} />} /><ActionFeedback state={feedback} />
    <div className="af-work-stack"><SettingsSection title="登记新变更" description="用明确的标题记录这次准备上线的内容。">
      <form onSubmit={(event) => { event.preventDefault(); void submit(); }}>
        <label className="af-field"><span>变更标题</span><Input value={title} onChange={(event) => { setTitle(event.target.value); feedback.clear(); }}
          required disabled={feedback.busy} placeholder="例如：补充退换货知识库" /></label>
        <Button type="primary" htmlType="submit" loading={feedback.busy} disabled={!title.trim()}>创建上线卡片</Button>
      </form>
    </SettingsSection><WorkspacePanel title="变更与效果" description="未填写的指标显示为“尚未记录”，与实际零值区分。">
      <FilterBar {...filter} placeholder="搜索变更标题" count={query.data ? filter.rows.length : undefined}
        options={[{ value: "all", label: "全部阶段" }, { value: "planned", label: "规划中" },
          { value: "measuring", label: "度量中" }, { value: "shipped", label: "已上线" }, { value: "draft", label: "草稿" }]} />
      <DataTable query={query} dataSource={filter.rows} columns={COLUMNS} emptyTitle={filter.filtered ? "没有匹配的变更" : "尚未登记上线变更"}
        emptyDescription="创建第一张上线卡片，开始记录变更目标与结果。" />
    </WorkspacePanel></div>
  </div>;
}
