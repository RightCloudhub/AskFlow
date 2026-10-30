import { FileTextOutlined } from "@ant-design/icons";
import type { CitationSource, Message } from "../../api/types";
import { useSourcePanel } from "../../stores/ui-store";
import { CitationTag } from "./CitationText";

type ConsultationRailProps = { messages: Message[]; status?: string; handoff: boolean };
const STATUS_COPY: Record<string, string> = { active: "智能助手正在为您服务", transferred: "人工客服接续处理", closed: "本次会话已结束" };

export function ConsultationRail({ messages, status, handoff }: ConsultationRailProps) {
  const openSources = useSourcePanel((state) => state.openSources);
  const latest = [...messages].reverse().find((message) => message.role === "assistant");
  const sources = Array.isArray(latest?.meta?.sources) ? latest.meta.sources as CitationSource[] : [];
  return <aside className="af-consultation-rail" aria-label="本次咨询详情">
    <section><h2>本次咨询</h2><div className="af-consultation-state"><span className={handoff ? "is-handoff" : ""} />
      <strong>{handoff ? "已转接人工客服" : STATUS_COPY[status ?? "active"] ?? "服务进行中"}</strong></div>
      <p>{handoff ? "客服将结合已有对话继续处理，您可以补充问题。" : "回答有据可查，问题也可以交由人工继续处理。"}</p>
    </section>
    <section><h2>最近回答的依据</h2>{sources.length ? <><ul className="af-consultation-sources">
      {sources.map((source, offset) => <li key={`${source.source}-${offset}`}>
        <CitationTag source={source} index={source.index ?? offset + 1} sources={sources} />
        <span>{source.source || "知识库文档"}</span>
      </li>)}
    </ul><button type="button" className="af-consultation-all" onClick={() => openSources(sources, "回答依据")}>
      <FileTextOutlined />查看全部依据</button></> : <p>有引用的回答出现后，来源会列在这里。</p>}</section>
    <section className="af-consultation-note"><h2>让问题更快解决</h2><p>查询订单时提供订单号；描述故障时说明发生时间与具体表现。</p></section>
  </aside>;
}
