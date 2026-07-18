import { FormEvent, useState } from "react";
import { Button, Input, Space } from "antd";
import { PlusOutlined } from "@ant-design/icons";

const { TextArea } = Input;

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
    <form onSubmit={(e) => void handleSubmit(e)}>
      <Space direction="vertical" style={{ width: "100%" }} size="middle">
        <Input
          placeholder="标题"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          required
        />
        <TextArea
          placeholder="描述"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          rows={3}
        />
        <Button
          type="primary"
          htmlType="submit"
          icon={<PlusOutlined />}
          loading={loading}
          disabled={!title.trim()}
        >
          提交
        </Button>
      </Space>
    </form>
  );
}
