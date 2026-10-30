import { useCallback, useState } from "react";
import { Button, List } from "antd";
import { Link, useSearchParams } from "react-router-dom";
import { mall, write } from "./client";
import { ActionForm, Feedback, useLoad, type Page, type Row } from "./shared";
import { useFeatures } from "../plugins/features";
import { MallPage, MallPanel } from "./presentation";

function Notices({ rows, reload }: { rows: Row[]; reload: () => Promise<void> }) {
  const [error, setError] = useState("");
  async function read(id: unknown) {
    try { await write(`/notify/${id}/read`, {}); await reload(); setError(""); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "标记失败"); }
  }
  return <MallPanel title="站内消息"><Feedback error={error} />
    <List className="af-mall-feed" dataSource={rows} locale={{ emptyText: "暂无站内消息。" }} renderItem={(row) => <List.Item>
      <div className="af-mall-message"><strong>{String(row.subject ?? "")}</strong><p>{String(row.body ?? "")}</p></div>
      {!row.read_at && <Button type="text" onClick={() => void read(row.id)}>标为已读</Button>}
    </List.Item>} />
  </MallPanel>;
}

export function Messages() {
  const [params] = useSearchParams();
  const { enabled } = useFeatures();
  const loader = useCallback(async () => {
    const notices = enabled("mall_notify") ? await mall<Page<Row>>("/notify") : { items: [] };
    const links = enabled("mall_support") ? await mall<Page<Row>>("/support") : { items: [] };
    return { notices, links };
  }, [enabled]);
  const query = useLoad(loader);
  return <MallPage title="消息与客服" description="跟进服务记录，接收订单、售后与钱包通知。">
    <Feedback {...query} />
    {enabled("mall_support") && <MallPanel title="联系商城客服" description="订单、退款或资金流水相关问题，会随会话一起交给客服。">
      <ActionForm label="提交问题" fields={[{ name: "title", label: "需要什么帮助？" }]}
        submit={async (values) => { await write("/support", { ...values, ticket: true,
          order_id: params.get("order_id"), wallet_journal_id: params.get("wallet_journal_id"), refund_id: params.get("refund_id"),
        }); await query.reload(); }} />
    </MallPanel>}
    {enabled("mall_support") && <MallPanel title="服务记录">
      <List className="af-mall-feed" dataSource={query.data?.links.items} locale={{ emptyText: "还没有服务记录。" }}
        renderItem={(row) => <List.Item><div className="af-mall-service-record">
          {enabled("agent") && <Link to={`/?conversation_id=${row.conversation_id}`}>打开客服会话</Link>}
          {enabled("ticket") && <Link to="/tickets">查看工单 {String(row.ticket_id ?? "")}</Link>}
        </div></List.Item>} />
    </MallPanel>}
    {enabled("mall_notify") && <Notices rows={query.data?.notices.items ?? []} reload={query.reload} />}
  </MallPage>;
}
