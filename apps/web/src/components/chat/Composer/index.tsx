import { FormEvent, KeyboardEvent, useState } from "react";
import { Button, Input, Tooltip } from "antd";
import { ArrowUpOutlined } from "@ant-design/icons";

const { TextArea } = Input;

type ComposerProps = {
  disabled?: boolean;
  sending?: boolean;
  placeholder?: string;
  onSend: (content: string) => void | Promise<void>;
};

export function Composer({
  disabled = false,
  sending = false,
  placeholder = "输入您的问题…",
  onSend,
}: ComposerProps) {
  const [value, setValue] = useState("");
  const [composing, setComposing] = useState(false);
  const blocked = disabled || sending;

  async function submit() {
    const text = value.trim();
    if (!text || blocked) return;
    setValue("");
    await onSend(text);
  }

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    void submit();
  }

  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    // Ignore Enter while an IME (e.g. Pinyin) is composing.
    if (
      e.key === "Enter" &&
      !e.shiftKey &&
      !composing &&
      !e.nativeEvent.isComposing
    ) {
      e.preventDefault();
      void submit();
    }
  }

  return (
    <div className="af-composer-wrap">
      <form
        className={`af-composer ${blocked ? "is-disabled" : ""}`}
        onSubmit={handleSubmit}
      >
        <TextArea
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          onCompositionStart={() => setComposing(true)}
          onCompositionEnd={() => setComposing(false)}
          placeholder={placeholder}
          disabled={disabled}
          variant="borderless"
          autoSize={{ minRows: 1, maxRows: 6 }}
          className="af-composer-input"
        />
        <div className="af-composer-bar">
          <span className="af-composer-hint">
            Enter 发送 · Shift + Enter 换行
          </span>
          <Tooltip title="发送">
            <Button
              type="primary"
              shape="circle"
              htmlType="submit"
              icon={<ArrowUpOutlined />}
              loading={sending}
              disabled={blocked || !value.trim()}
              className="af-composer-send"
              aria-label="发送"
            />
          </Tooltip>
        </div>
      </form>
      <p className="af-composer-foot">
        回答基于企业知识库生成，重要信息请以官方说明为准
      </p>
    </div>
  );
}
