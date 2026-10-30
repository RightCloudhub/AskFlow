import { BrandMark } from "../../layout/BrandMark";

type ChatEmptyProps = { hint: string; suggestions: string[]; onSuggest?: (text: string) => void };

export function ChatEmpty({ hint, suggestions, onSuggest }: ChatEmptyProps) {
  return <div className="af-chat-empty"><BrandMark /><h2>从一个问题开始</h2><p>{hint}</p>
    {onSuggest && suggestions.length > 0 && <div className="af-suggest-grid">{suggestions.map((text) =>
      <button key={text} type="button" className="af-suggest" onClick={() => onSuggest(text)}>{text}</button>
    )}</div>}
  </div>;
}
