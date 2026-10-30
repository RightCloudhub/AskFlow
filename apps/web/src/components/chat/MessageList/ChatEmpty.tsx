import { ArrowRightOutlined } from "@ant-design/icons";
import { BrandMark } from "../../layout/BrandMark";

type ChatEmptyProps = { hint: string; suggestions: string[]; onSuggest?: (text: string) => void };
const QUESTION_COPY: Record<string, { title: string; description: string }> = {
  "退货政策是什么？": { title: "了解退货政策", description: "退货条件、申请方式与处理流程" },
  "帮我查一下订单物流": { title: "查询订单物流", description: "补充订单号，继续跟进配送进度" },
  "发票怎么开？": { title: "申请开具发票", description: "了解开票资料与申请方式" },
  "转人工客服": { title: "联系人工客服", description: "把问题与对话交给客服继续处理" },
};

export function ChatEmpty({ hint, suggestions, onSuggest }: ChatEmptyProps) {
  return <section className="af-chat-empty"><div className="af-chat-welcome">
    <BrandMark /><h2>今天，有什么需要解决？</h2><p>{hint}</p></div>
    {onSuggest && suggestions.length > 0 && <section className="af-chat-questions" aria-labelledby="af-question-heading">
      <h3 id="af-question-heading">从常见问题开始</h3><div className="af-suggest-grid">{suggestions.map((text) => {
        const copy = QUESTION_COPY[text] ?? { title: text, description: "开始咨询，继续补充您的问题" };
        return <button key={text} type="button" className="af-suggest" onClick={() => onSuggest(text)}>
          <span><strong>{copy.title}</strong><small>{copy.description}</small></span><ArrowRightOutlined />
        </button>;
      })}</div>
    </section>}
  </section>;
}
