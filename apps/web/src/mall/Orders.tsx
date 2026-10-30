import { useCallback } from "react";
import { Descriptions, List, Typography } from "antd";
import { Link, useParams } from "react-router-dom";
import { mall, money } from "./client";
import { useLoad, type Page } from "./shared";
import { OrderActions, type Order } from "./OrderActions";
import { MallPage, MallPanel, MallStatus, formatDate } from "./presentation";
import { CursorNav, MallQuery, QueryRefresh, useCursor } from "./query-view";
import { FilterBar } from "../components/admin/workspace";
import { useRecordFilter } from "../components/admin/use-record-filter";
import { OrderItems, OrderProgress } from "./order-progress";

const ORDER_STATES = [{ value: "all", label: "全部状态" }, { value: "PENDING_PAYMENT", label: "待支付" },
  { value: "PAID", label: "已支付" }, { value: "SHIPPED", label: "已发货" }, { value: "DELIVERED", label: "已送达" },
  { value: "COMPLETED", label: "已完成" }, { value: "CANCELLED", label: "已取消" },
  { value: "PARTIALLY_REFUNDED", label: "部分退款" }, { value: "REFUNDED", label: "已退款" }];

export function Orders() {
  const paging = useCursor();
  const loader = useCallback(() => mall<Page<Order>>(`/order/orders?cursor=${encodeURIComponent(paging.cursor)}`), [paging.cursor]);
  const query = useLoad(loader);
  const filter = useRecordFilter({ rows: query.data?.items ?? [], fields: ["id"], statusField: "status" });
  return <MallPage title="我的订单" description="付款、配送和售后进度，都从这笔订单继续。" actions={<Link to="/shop">继续选购</Link>}>
    <MallPanel title="订单记录" actions={<QueryRefresh query={query} />} className="af-order-records">
      <FilterBar {...filter} count={query.data ? filter.rows.length : undefined} placeholder="搜索本页订单号" options={ORDER_STATES} />
      <MallQuery query={query}><List className="af-order-list" dataSource={filter.rows}
        locale={{ emptyText: filter.filtered ? "没有匹配的订单，请调整筛选。" : "还没有订单，选好商品后从购物车下单。" }} renderItem={(order) => <List.Item>
          <div className="af-order-identity"><Link to={`/shop/orders/${order.id}`}>订单详情</Link>
            <Typography.Text type="secondary" className="af-order-id" copyable={{ text: order.id }}>订单号 {order.id}</Typography.Text>
            <span className="af-record-secondary">{formatDate(order.created_at)}</span></div>
          <div className="af-order-result"><MallStatus value={order.status} /><strong className="af-order-amount">{money(order.total_cents, order.currency)}</strong></div>
        </List.Item>} /></MallQuery>
      <CursorNav paging={paging} nextCursor={query.data?.next_cursor} loading={query.loading} />
    </MallPanel>
  </MallPage>;
}

export function OrderDetail() {
  const { id } = useParams();
  const loader = useCallback(() => mall<Order>(`/order/orders/${encodeURIComponent(id ?? "")}`), [id]);
  const query = useLoad(loader);
  return <MallPage title="订单详情" description="查看这笔订单的进度、金额与可用服务。" actions={<Link to="/shop/orders">返回订单</Link>}>
    <MallPanel title="订单进度" actions={<QueryRefresh query={query} />}><MallQuery query={query}>
      {query.data && <OrderProgress order={query.data} />}
    </MallQuery></MallPanel>
    {query.data && <div className="af-mall-columns af-order-workspace"><MallPanel title="订单信息">
      <Descriptions className="af-mall-description-list" column={1} items={[
        { key: "id", label: "订单号", children: <Typography.Text copyable={{ text: query.data.id }}>{query.data.id}</Typography.Text> },
        { key: "total", label: "订单金额", children: money(query.data.total_cents, query.data.currency) },
        { key: "refund", label: "已退款", children: money(query.data.refunded_cents, query.data.currency) },
        { key: "created", label: "下单时间", children: formatDate(query.data.created_at) },
        { key: "tracking", label: "物流单号", children: query.data.tracking_number || "—" },
      ]} /><OrderItems order={query.data} />
    </MallPanel><MallPanel title="订单服务"><OrderActions order={query.data} reload={query.reload} /></MallPanel></div>}
  </MallPage>;
}
