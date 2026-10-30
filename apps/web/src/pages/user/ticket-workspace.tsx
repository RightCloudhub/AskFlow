import { Card, Col, Row, Segmented } from "antd";
import { AppstoreOutlined, UnorderedListOutlined } from "@ant-design/icons";
import { TicketBoard } from "../../components/ticket/TicketBoard";
import { TicketForm } from "../../components/ticket/TicketForm";
import { TicketList } from "../../components/ticket/TicketList";
import type { useTicketsPage } from "./ticket-state";
import { FilterBar, QueryFeedback, RefreshButton } from "../../components/admin/workspace";
import { ActionFeedback } from "../../components/common/action-feedback";

type TicketState = ReturnType<typeof useTicketsPage>;
const WORKSPACE_GUTTER = 24;
const GRID_FULL = 24;
const FORM_SPAN = 8;
const LIST_SPAN = 16;
const TICKET_STATES = [{ value: "all", label: "全部状态" }, { value: "pending", label: "待处理" },
  { value: "processing", label: "处理中" }, { value: "resolved", label: "已解决" }, { value: "closed", label: "已关闭" }];

function TicketListPanel({ state }: { state: TicketState }) {
  return <Card title="工单列表" className="af-user-card" extra={<Segmented value={state.view}
    onChange={(value) => state.setView(value as "list" | "board")} options={[
      { value: "list", icon: <UnorderedListOutlined />, label: "列表" },
      { value: "board", icon: <AppstoreOutlined />, label: "看板" },
    ]} />}><div className="af-ticket-list-tools"><RefreshButton query={state.tickets} /></div>
    <FilterBar {...state.filter} count={state.tickets.data ? state.rows.length : undefined} placeholder="搜索问题标题或工单号" options={TICKET_STATES} />
    <QueryFeedback query={state.tickets} /><ActionFeedback state={state.feedback} />
    {state.view === "list" ? <TicketList rows={state.rows} loading={state.tickets.isLoading}
      closingId={state.close.isPending ? (state.close.variables ?? null) : null}
      onClose={(id) => void state.closeTicket(id)} onSelect={state.setSelected} /> : <TicketBoard rows={state.rows} onSelect={state.setSelected} />}
  </Card>;
}

export function TicketWorkspace({ state }: { state: TicketState }) {
  return <Row gutter={[WORKSPACE_GUTTER, WORKSPACE_GUTTER]}>
    <Col xs={GRID_FULL} lg={FORM_SPAN}><Card title="新建工单" className="af-user-card">
      <TicketForm loading={state.create.isPending} onSubmit={async (payload) => { await state.create.mutateAsync(payload); }} />
    </Card></Col><Col xs={GRID_FULL} lg={LIST_SPAN}><TicketListPanel state={state} /></Col>
  </Row>;
}
