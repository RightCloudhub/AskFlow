import { RecordWorkspace } from "../../components/admin/record-workspace";
import { useState } from "react";
import { PageHeader } from "../../components/admin";
import { FilterBar, RefreshButton, WorkspacePanel } from "../../components/admin/workspace";
import { useRecordFilter } from "../../components/admin/use-record-filter";
import { ActionFeedback, useActionFeedback } from "../../components/common/action-feedback";
import { HandoffInbox } from "../../components/handoff/Inbox";
import { SessionDetail } from "../../components/handoff/SessionDetail";
import { useClaimHandoff, useHandoffs, useReturnHandoff } from "../../hooks/use-ops";
import { useMe } from "../../hooks/use-auth";
import type { Handoff } from "../../api/types";

export function HandoffsPage() {
  const query = useHandoffs();
  const me = useMe();
  const claim = useClaimHandoff();
  const ret = useReturnHandoff();
  const feedback = useActionFeedback();
  const [selected, setSelected] = useState<Handoff | null>(null);
  const filter = useRecordFilter({ rows: query.data ?? [], fields: ["user_name", "summary", "conversation_id"], statusField: "status" });
  const current = query.data?.find((row) => row.id === selected?.id) ?? selected;
  async function onClaim(id: string) {
    await feedback.run(async () => setSelected(await claim.mutateAsync(id)), "会话已认领，可以开始回复客户。");
  }
  async function onReturn(id: string) {
    const done = await feedback.run(() => ret.mutateAsync(id), "会话已交还智能助手。");
    if (done && selected?.id === id) setSelected(null);
  }
  return <div className="af-page"><PageHeader title="人工接管" subtitle="先认领，再回复。会话列表每 15 秒自动更新。"
    actions={<RefreshButton query={query} />} /><ActionFeedback state={feedback} />
    <RecordWorkspace rows={query.data} field="status" states={[{ value: "queued", label: "等待认领" }, { value: "claimed", label: "已认领" }, { value: "timed_out", label: "已超时" }]}
      selected={filter.status} onSelect={filter.onStatus}>
      <WorkspacePanel title="人工服务队列" description="查看客户问题摘要，认领后可展开历史消息。">
      <FilterBar {...filter} placeholder="搜索客户、问题摘要或会话编号" count={query.data ? filter.rows.length : undefined}
        options={[{ value: "all", label: "全部状态" }, { value: "queued", label: "等待认领" },
          { value: "claimed", label: "已认领" }, { value: "returned", label: "已交还" }, { value: "timed_out", label: "已超时" }]} />
      <HandoffInbox rows={filter.rows} query={query} currentUserId={me.data?.id ?? null}
        claimingId={claim.isPending ? claim.variables : null} returningId={ret.isPending ? ret.variables : null}
        onClaim={(id) => void onClaim(id)} onReturn={(id) => void onReturn(id)} onSelect={setSelected} />
    </WorkspacePanel>
    </RecordWorkspace>
    <SessionDetail open={Boolean(selected)} session={current} onClose={() => setSelected(null)} />
  </div>;
}
