import { useCallback } from "react";
import { Button, Card, List, Space, Typography } from "antd";
import { Link, useSearchParams } from "react-router-dom";
import { mall, write } from "./client";
import { ActionForm, Feedback, useLoad, type Page, type Row } from "./shared";
import { useFeatures } from "../plugins/features";

export function Messages() {
  const [params] = useSearchParams();
  const { enabled } = useFeatures();
  const loader = useCallback(async () => {
    const notices = enabled("mall_notify") ? await mall<Page<Row>>("/notify") : { items: [] };
    const links = enabled("mall_support") ? await mall<Page<Row>>("/support") : { items: [] };
    return { notices, links };
  }, [enabled]);
  const query = useLoad(loader);
  return <Card title="消息与客服"><Feedback {...query} />
    {enabled("mall_support") && <ActionForm label="创建客服会话与工单" fields={[{ name: "title", label: "需要什么帮助？" }]}
      submit={async (values) => { await write("/support", { ...values, ticket: true,
        order_id: params.get("order_id"), wallet_journal_id: params.get("wallet_journal_id"), refund_id: params.get("refund_id"),
      }); await query.reload(); }} />}
    <List header="服务记录" dataSource={query.data?.links.items} renderItem={(row) => <List.Item>
      <Space>{enabled("agent") && <Link to={`/?conversation_id=${row.conversation_id}`}>客服会话</Link>}
        <Link to="/tickets">工单 {String(row.ticket_id ?? "")}</Link></Space>
    </List.Item>} />
    <List header="站内消息" dataSource={query.data?.notices.items} renderItem={(row) => <List.Item>
      <Space direction="vertical"><Typography.Text strong>{String(row.subject)}</Typography.Text>
        <Typography.Text>{String(row.body)}</Typography.Text></Space>
      {!row.read_at && <Button onClick={() => { void write(`/notify/${row.id}/read`, {}).then(query.reload); }}>标为已读</Button>}
    </List.Item>} />
  </Card>;
}
