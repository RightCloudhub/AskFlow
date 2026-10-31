import { Button } from "antd";
import { ArrowLeftOutlined } from "@ant-design/icons";
import type { Handoff, User } from "../../../api/types";
import { SessionFlow } from "./session-flow";

export type SessionDetailProps = {
  session: Handoff | null; currentUser?: User; busy: boolean; onBusyChange: (busy: boolean) => void;
  draft: string; onDraftChange: (text: string) => void; onBack: () => void;
};

export function SessionDetail(props: SessionDetailProps) {
  return <section className="af-service-detail" aria-label="接管工作台">
    <div className="af-service-back"><Button type="text" icon={<ArrowLeftOutlined />} disabled={props.busy}
      onClick={props.onBack}>返回服务队列</Button></div>
    {props.session ? <SessionFlow key={props.session.id} {...props} session={props.session} /> :
      <div className="af-handoff-empty af-service-welcome"><h2>从一段对话开始</h2>
        <p>选择客户，查看转接摘要并开始人工服务。</p><span>AskFlow · 让每一次转接都有上下文</span></div>}
  </section>;
}
