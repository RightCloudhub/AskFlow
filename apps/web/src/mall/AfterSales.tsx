import { useCallback, useState } from "react";
import { Button, Card, Descriptions, List, Space, Typography } from "antd";
import { Link, useSearchParams } from "react-router-dom";
import { mall, money } from "./client";
import { Feedback, useLoad, type Page, type Row } from "./shared";
import { useFeatures } from "../plugins/features";

export function AfterSales() {
  const { enabled } = useFeatures();
  const [cursor, setCursor] = useState("");
  const load = useCallback(() => mall<Page<Row>>(`/order/refunds?cursor=${encodeURIComponent(cursor)}`), [cursor]);
  const query = useLoad(load);
  return <Card title="我的售后"><Feedback {...query} />
    <List dataSource={query.data?.items} renderItem={(row) => <List.Item><Space direction="vertical">
      <Link to={`/shop/orders/${row.order_id}`}>查看关联订单</Link>
      <Typography.Text>{String(row.status)} · {money(Number(row.amount_cents))}</Typography.Text>
      {enabled("mall_support") && <Link to={`/shop/messages?refund_id=${row.id}`}>联系售后客服</Link>}
    </Space></List.Item>} />
    {query.data?.next_cursor && <Button onClick={() => setCursor(query.data!.next_cursor!)}>下一页</Button>}
  </Card>;
}

export function PaymentResult() {
  const [params] = useSearchParams();
  const id = params.get("payment_id");
  const load = useCallback(() => id ? mall<Row>(`/payment/${encodeURIComponent(id)}`) : Promise.resolve({}), [id]);
  const query = useLoad<Row>(load);
  return <Card title="支付结果"><Feedback {...query} />
    <Descriptions items={[
      { key: "status", label: "支付状态", children: String(query.data?.status ?? "请选择支付单") },
      { key: "amount", label: "支付金额", children: money(Number(query.data?.amount_cents ?? 0)) },
    ]} /><Button onClick={() => { void query.reload(); }}>刷新结果</Button>
    <Link to="/shop/orders">返回订单</Link>
  </Card>;
}
