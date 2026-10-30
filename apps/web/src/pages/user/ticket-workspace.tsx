import { Card, Col, Row, Segmented } from "antd";
import { AppstoreOutlined, UnorderedListOutlined } from "@ant-design/icons";
import { TicketBoard } from "../../components/ticket/TicketBoard";
import { TicketForm } from "../../components/ticket/TicketForm";
import { TicketList } from "../../components/ticket/TicketList";
import type { useTicketsPage } from "./ticket-state";

type TicketState = ReturnType<typeof useTicketsPage>;
const WORKSPACE_GUTTER = 24;
const GRID_FULL = 24;
const FORM_SPAN = 8;
const LIST_SPAN = 16;

function TicketListPanel({ state }: { state: TicketState }) {
  return <Card title="工单列表" className="af-user-card" extra={<Segmented value={state.view}
    onChange={(value) => state.setView(value as "list" | "board")} options={[
      { value: "list", icon: <UnorderedListOutlined />, label: "列表" },
      { value: "board", icon: <AppstoreOutlined />, label: "看板" },
    ]} />}>
    {state.view === "list" ? <TicketList rows={state.rows} loading={state.tickets.isLoading}
      closingId={state.close.isPending ? (state.close.variables ?? null) : null}
      onClose={(id) => void state.close.mutateAsync(id)} /> : <TicketBoard rows={state.rows} onSelect={state.setSelected} />}
  </Card>;
}

export function TicketWorkspace({ state }: { state: TicketState }) {
  return <Row gutter={[WORKSPACE_GUTTER, WORKSPACE_GUTTER]}>
    <Col xs={GRID_FULL} lg={FORM_SPAN}><Card title="新建工单" className="af-user-card">
      <TicketForm loading={state.create.isPending} onSubmit={async (payload) => { await state.create.mutateAsync(payload); }} />
    </Card></Col><Col xs={GRID_FULL} lg={LIST_SPAN}><TicketListPanel state={state} /></Col>
  </Row>;
}
