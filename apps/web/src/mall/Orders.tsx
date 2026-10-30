import { useCallback, useState } from "react";
import { Button, Descriptions, List } from "antd";
import { Link, useParams } from "react-router-dom";
import { mall, money } from "./client";
import { Feedback, useLoad, type Page } from "./shared";
import { OrderActions, type Order } from "./OrderActions";
import { MallPage, MallPanel, MallStatus } from "./presentation";

export function Orders() {
  const [cursor, setCursor] = useState("");
  const loader = useCallback(() => mall<Page<Order>>(`/order/orders?cursor=${encodeURIComponent(cursor)}`), [cursor]);
  const query = useLoad(loader);
  return <MallPage title="我的订单" description="查看付款、配送与售后进度。" actions={<Link to="/shop">继续选购</Link>}>
    <Feedback {...query} /><MallPanel title="订单记录">
      <List className="af-order-list" dataSource={query.data?.items} locale={{ emptyText: "还没有订单，选好商品后从购物车下单。" }}
        renderItem={(order) => <List.Item>
          <div className="af-order-identity"><Link to={`/shop/orders/${order.id}`}>查看订单</Link>
            <span className="af-order-id">订单号 {order.id}</span></div>
          <MallStatus value={order.status} /><strong className="af-order-amount">{money(order.total_cents, order.currency)}</strong>
        </List.Item>} />
      {query.data?.next_cursor && <div className="af-mall-pagination">
        <Button onClick={() => setCursor(query.data!.next_cursor!)}>下一页订单</Button>
      </div>}
    </MallPanel>
  </MallPage>;
}

export function OrderDetail() {
  const { id } = useParams();
  const loader = useCallback(() => mall<Order>(`/order/orders/${id}`), [id]);
  const query = useLoad(loader);
  return <MallPage title="订单详情" description="订单金额、当前状态与可用操作。" actions={<Link to="/shop/orders">返回订单列表</Link>}>
    <Feedback {...query} />
    {query.data && <><MallPanel title="订单信息" className="af-order-summary">
      <Descriptions className="af-mall-description-list" column={{ xs: 1, sm: 2, md: 3 }} items={[
        { key: "id", label: "订单号", children: query.data.id },
        { key: "status", label: "状态", children: <MallStatus value={query.data.status} /> },
        { key: "total", label: "金额", children: money(query.data.total_cents, query.data.currency) },
      ]} />
    </MallPanel><MallPanel title="订单服务"><OrderActions order={query.data} reload={query.reload} /></MallPanel></>}
  </MallPage>;
}

