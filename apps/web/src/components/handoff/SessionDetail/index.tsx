import { useState } from "react";
import {
  Button,
  Descriptions,
  Drawer,
  Empty,
  Input,
  Spin,
  Tag,
  Typography,
} from "antd";
import { SendOutlined } from "@ant-design/icons";
import { StatusBadge } from "../../admin";
import { MarkdownBody } from "../../chat/MarkdownBody";
import type { Handoff, Message } from "../../../api/types";
import {
  useHandoffMessages,
  useStaffReply,
} from "../../../hooks/use-ops";

const { Paragraph, Text } = Typography;
const { TextArea } = Input;

type SessionDetailProps = {
  open: boolean;
  session: Handoff | null;
  onClose: () => void;
};

export function SessionDetail({ open, session, onClose }: SessionDetailProps) {
  const canChat = session?.status === "claimed";
  const msgsQ = useHandoffMessages(open && canChat ? session?.id ?? null : null);
  const reply = useStaffReply();
  const [text, setText] = useState("");

  async function onSend() {
    if (!session || !text.trim()) return;
    await reply.mutateAsync({ id: session.id, content: text.trim() });
    setText("");
  }

  return (
    <Drawer
      title="接管工作台"
      open={open}
      onClose={onClose}
      width={480}
      destroyOnClose
    >
      {!session ? null : (
        <>
          <Descriptions column={1} size="small" bordered style={{ marginBottom: 12 }}>
            <Descriptions.Item label="状态">
              <StatusBadge value={session.status} />
            </Descriptions.Item>
            <Descriptions.Item label="会话">
              <code className="af-mono">{session.conversation_id}</code>
            </Descriptions.Item>
            <Descriptions.Item label="意图">
              {session.intent || "handoff"}
            </Descriptions.Item>
            <Descriptions.Item label="认领人">
              {session.claimed_by ? (
                <Tag color="blue">{session.claimed_by.slice(0, 8)}…</Tag>
              ) : (
                <Text type="secondary">未认领</Text>
              )}
            </Descriptions.Item>
          </Descriptions>
          <Paragraph type="secondary" style={{ marginBottom: 4 }}>
            摘要
          </Paragraph>
          <Paragraph>{session.summary || "（无摘要）"}</Paragraph>

          {canChat ? (
            <div className="af-staff-chat">
              <Text strong>会话消息</Text>
              <div className="af-staff-msgs">
                {msgsQ.isLoading ? (
                  <Spin size="small" />
                ) : (msgsQ.data ?? []).length === 0 ? (
                  <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无消息" />
                ) : (
                  (msgsQ.data ?? []).map((m) => <StaffMsg key={m.id} message={m} />)
                )}
              </div>
              <TextArea
                rows={3}
                value={text}
                onChange={(e) => setText(e.target.value)}
                placeholder="以座席身份回复…"
                disabled={reply.isPending}
              />
              <Button
                type="primary"
                icon={<SendOutlined />}
                loading={reply.isPending}
                disabled={!text.trim()}
                onClick={() => void onSend()}
                style={{ marginTop: 8 }}
                block
              >
                发送座席回复
              </Button>
            </div>
          ) : (
            <Paragraph type="secondary">认领后可查看消息并回复用户。</Paragraph>
          )}
        </>
      )}
    </Drawer>
  );
}

function StaffMsg({ message }: { message: Message }) {
  const label =
    message.role === "user"
      ? "用户"
      : message.role === "staff"
        ? "座席"
        : message.role === "assistant"
          ? "助手"
          : message.role;
  return (
    <div className={`af-staff-msg af-staff-msg--${message.role}`}>
      <span className="af-staff-msg-role">{label}</span>
      {message.role === "user" ? (
        <div className="af-bubble-plain">{message.content}</div>
      ) : (
        <MarkdownBody content={message.content} />
      )}
    </div>
  );
}
