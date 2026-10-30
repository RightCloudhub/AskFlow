import { useState, type FormEvent, type KeyboardEvent } from "react";
import { Button, Input, Tooltip } from "antd";
import { ArrowUpOutlined } from "@ant-design/icons";

type ComposerProps = {
  disabled?: boolean; sending?: boolean; placeholder?: string;
  onSend: (content: string) => void | Promise<void>;
};
const TEXTAREA_ROWS = { minRows: 1, maxRows: 6 };

function useComposer({ disabled, sending, onSend }: ComposerProps) {
  const [value, setValue] = useState("");
  const [composing, setComposing] = useState(false);
  const blocked = disabled || sending;
  async function submit() {
    const text = value.trim();
    if (!text || blocked) return;
    setValue(""); await onSend(text);
  }
  function handleSubmit(event: FormEvent) { event.preventDefault(); void submit(); }
  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key !== "Enter" || event.shiftKey || composing || event.nativeEvent.isComposing) return;
    event.preventDefault(); void submit();
  }
  return { value, setValue, setComposing, blocked, handleSubmit, handleKeyDown };
}

export function Composer({ disabled = false, sending = false, placeholder = "输入您的问题…", onSend }: ComposerProps) {
  const state = useComposer({ disabled, sending, onSend });
  return <div className="af-composer-wrap"><form className={`af-composer ${state.blocked ? "is-disabled" : ""}`} onSubmit={state.handleSubmit}>
    <Input.TextArea value={state.value} onChange={(event) => state.setValue(event.target.value)} onKeyDown={state.handleKeyDown}
      onCompositionStart={() => state.setComposing(true)} onCompositionEnd={() => state.setComposing(false)}
      placeholder={placeholder} disabled={disabled} variant="borderless" autoSize={TEXTAREA_ROWS}
      aria-label="输入客服问题" className="af-composer-input" />
    <div className="af-composer-bar"><span className="af-composer-hint">Enter 发送 · Shift + Enter 换行</span>
      <Tooltip title="发送"><Button type="primary" shape="circle" htmlType="submit" icon={<ArrowUpOutlined />}
        loading={sending} disabled={state.blocked || !state.value.trim()} className="af-composer-send" aria-label="发送" /></Tooltip>
    </div>
  </form><p className="af-composer-foot">回答基于企业知识库生成，重要信息请以官方说明为准</p></div>;
}
