import { Link } from "react-router-dom";
import { Alert, Button } from "antd";
import { ArrowLeftOutlined } from "@ant-design/icons";
import { BrandMark } from "../../components/layout/BrandMark";
import { TicketDetail } from "../../components/ticket/TicketDetail";
import { PageHeader } from "../../components/admin";
import { useTicketsPage } from "./ticket-state";
import { TicketWorkspace } from "./ticket-workspace";

export function TicketsPage() {
  const state = useTicketsPage();
  return <div className="af-user-page"><header className="af-user-topbar">
    <Link to="/" className="af-user-topbar-back"><Button type="text" icon={<ArrowLeftOutlined />}>返回对话</Button></Link>
    <span className="af-user-topbar-brand"><BrandMark /><strong>AskFlow</strong></span>
    <span className="af-user-topbar-spacer" />
  </header><div className="af-user-body">
    <PageHeader title="我的工单" subtitle={`共 ${state.rows.length} 个工单，${state.openCount} 个处理中。提交后客服会尽快跟进。`} />
    {state.error && <div className="af-ticket-error"><Alert type="error" showIcon title={state.error} /></div>}
    <TicketWorkspace state={state} />
  </div><TicketDetail open={Boolean(state.selected)} ticket={state.selected} onClose={() => state.setSelected(null)} /></div>;
}
