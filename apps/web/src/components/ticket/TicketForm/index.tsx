import { FormEvent, useState } from "react";
import { Button, Input } from "antd";
import { SendOutlined } from "@ant-design/icons";

const { TextArea } = Input;
const TITLE_MAX = 80;

type TicketFormProps = {
  loading?: boolean;
  onSubmit: (p: { title: string; description: string }) => void | Promise<void>;
};

export function TicketForm({ loading, onSubmit }: TicketFormProps) {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!title.trim()) return;
    await onSubmit({ title: title.trim(), description });
    setTitle("");
    setDescription("");
  }

  return (
    <form className="af-ticket-form" onSubmit={(e) => void handleSubmit(e)}>
      <label className="af-field">
        <span>问题标题</span>
        <Input
          placeholder="例如：收到的商品有破损"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          maxLength={TITLE_MAX}
          showCount
          required
        />
      </label>
      <label className="af-field">
        <span>详细描述</span>
        <TextArea
          placeholder="请描述问题经过、订单号等信息，便于客服快速处理"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          autoSize={{ minRows: 4, maxRows: 8 }}
        />
      </label>
      <Button
        type="primary"
        htmlType="submit"
        icon={<SendOutlined />}
        loading={loading}
        disabled={!title.trim()}
        block
      >
        提交工单
      </Button>
    </form>
  );
}
