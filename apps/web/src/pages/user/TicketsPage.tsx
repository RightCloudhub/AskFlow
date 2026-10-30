import { Link } from "react-router-dom";
import { Button } from "antd";
import { ArrowLeftOutlined } from "@ant-design/icons";
import { BrandMark } from "../../components/layout/BrandMark";
import { WorkspaceSwitcher } from "../../components/layout/WorkspaceSwitcher";
import { TicketDetail } from "../../components/ticket/TicketDetail";
import { PageHeader } from "../../components/admin";
import { useTicketsPage } from "./ticket-state";
import { TicketWorkspace } from "./ticket-workspace";

export function TicketsPage() {
  const state = useTicketsPage();
  return <div className="af-user-page"><header className="af-user-topbar">
    <Link to="/" className="af-user-topbar-brand"><BrandMark /><strong>AskFlow</strong></Link>
    <Link to="/" className="af-user-topbar-back"><Button type="text" icon={<ArrowLeftOutlined />}>返回对话</Button></Link>
    <div className="af-user-workspace-switch"><WorkspaceSwitcher current="chat" /></div>
  </header><main className="af-user-body">
    <PageHeader title="我的工单" subtitle={state.tickets.data ? `共 ${state.allRows.length} 个工单，${state.openCount} 个处理中。` : "提交客服问题，跟进处理进度。"} />
    <TicketWorkspace state={state} />
  </main><TicketDetail open={Boolean(state.selected)} ticket={state.selected} onClose={() => state.setSelected(null)} /></div>;
}
