import { useState } from "react";
import { Button, Drawer, Segmented } from "antd";
import { AppstoreOutlined, PlusOutlined, UnorderedListOutlined } from "@ant-design/icons";
import { TicketBoard } from "../../components/ticket/TicketBoard";
import { TicketForm } from "../../components/ticket/TicketForm";
import { TicketList } from "../../components/ticket/TicketList";
import type { useTicketsPage } from "./ticket-state";
import { FilterBar, QueryFeedback, RefreshButton, WorkspacePanel } from "../../components/admin/workspace";
import { ActionFeedback } from "../../components/common/action-feedback";

type TicketState = ReturnType<typeof useTicketsPage>;
const TICKET_STATES = [{ value: "all", label: "全部状态" }, { value: "pending", label: "待处理" },
  { value: "processing", label: "处理中" }, { value: "resolved", label: "已解决" }, { value: "closed", label: "已关闭" }];

export function TicketWorkspace({ state }: { state: TicketState }) {
  const [creating, setCreating] = useState(false);
  return <><WorkspacePanel title="服务记录" actions={<div className="af-work-actions">
    <Segmented value={state.view} onChange={(value) => state.setView(value as "list" | "board")} options={[
      { value: "list", icon: <UnorderedListOutlined />, label: "列表" },
      { value: "board", icon: <AppstoreOutlined />, label: "看板" },
    ]} /><Button type="primary" icon={<PlusOutlined />} onClick={() => setCreating(true)}>新建工单</Button></div>}>
    <div className="af-ticket-list-tools"><RefreshButton query={state.tickets} /></div>
    <FilterBar {...state.filter} count={state.tickets.data ? state.rows.length : undefined}
      placeholder="搜索问题标题或工单号" options={TICKET_STATES} />
    <QueryFeedback query={state.tickets} /><ActionFeedback state={state.feedback} />
    {state.view === "list" ? <TicketList rows={state.rows} loading={state.tickets.isLoading}
      closingId={state.close.isPending ? (state.close.variables ?? null) : null}
      onClose={(id) => void state.closeTicket(id)} onSelect={state.setSelected} /> : <TicketBoard rows={state.rows} onSelect={state.setSelected} />}
  </WorkspacePanel><Drawer title="提交新的客服问题" open={creating} onClose={() => setCreating(false)} destroyOnHidden>
    <p className="af-ticket-create-intro">请说明问题和需要的帮助，客服将通过工单继续跟进。</p>
    <TicketForm loading={state.create.isPending} onSubmit={async (payload) => {
      await state.create.mutateAsync(payload); setCreating(false);
    }} />
  </Drawer></>;
}
