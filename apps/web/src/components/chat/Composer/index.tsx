import { FormEvent, KeyboardEvent, useState } from "react";
import { Button, Input } from "antd";
import { SendOutlined } from "@ant-design/icons";

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
  placeholder = "输入问题，Enter 发送，Shift+Enter 换行",
  onSend,
}: ComposerProps) {
  const [value, setValue] = useState("");
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
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void submit();
    }
  }

  return (
    <form className="af-composer" onSubmit={handleSubmit}>
      <TextArea
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        disabled={blocked}
        autoSize={{ minRows: 2, maxRows: 6 }}
        className="af-composer-input"
      />
      <Button
        type="primary"
        htmlType="submit"
        icon={<SendOutlined />}
        loading={sending}
        disabled={blocked || !value.trim()}
        className="af-composer-send"
      >
        发送
      </Button>
    </form>
  );
}
