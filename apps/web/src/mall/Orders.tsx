import { useCallback, useState } from "react";
import { Button, Card, Descriptions, List, Tag, Typography } from "antd";
import { Link, useParams } from "react-router-dom";
import { mall, money } from "./client";
import { Feedback, useLoad, type Page } from "./shared";
import { OrderActions, type Order } from "./OrderActions";

export function Orders() {
  const [cursor, setCursor] = useState("");
  const loader = useCallback(() => mall<Page<Order>>(`/order/orders?cursor=${encodeURIComponent(cursor)}`), [cursor]);
  const query = useLoad(loader);
  return <Card title="我的订单"><Feedback {...query} />
    <List dataSource={query.data?.items} renderItem={(order) => <List.Item>
      <Link to={`/shop/orders/${order.id}`}>{order.id}</Link>
      <Tag>{order.status}</Tag><Typography.Text>{money(order.total_cents, order.currency)}</Typography.Text>
    </List.Item>} />
    {query.data?.next_cursor && <Button onClick={() => setCursor(query.data!.next_cursor!)}>下一页</Button>}
  </Card>;
}

export function OrderDetail() {
  const { id } = useParams();
  const loader = useCallback(() => mall<Order>(`/order/orders/${id}`), [id]);
  const query = useLoad(loader);
  return <Card title="订单详情"><Feedback {...query} />
    {query.data && <><Descriptions items={[
      { key: "id", label: "订单号", children: query.data.id },
      { key: "status", label: "状态", children: query.data.status },
      { key: "total", label: "金额", children: money(query.data.total_cents, query.data.currency) },
    ]} /><OrderActions order={query.data} reload={query.reload} /></>}
  </Card>;
}

