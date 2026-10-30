import { MallStatus } from "./presentation";
import type { Order } from "./OrderActions";
import { money } from "./client";

const STAGES = [{ state: "PENDING_PAYMENT", label: "待支付" }, { state: "PAID", label: "已支付" },
  { state: "SHIPPED", label: "已发货" }, { state: "DELIVERED", label: "已送达" }, { state: "COMPLETED", label: "已完成" }];
const ORDER_GUIDANCE: Record<string, string> = {
  PENDING_PAYMENT: "订单等待付款，可在订单服务中完成支付或取消订单。",
  PAID: "订单已付款，等待商家安排发货。",
  SHIPPED: "订单已发货，收到商品并核对后可确认收货。",
  DELIVERED: "商品已送达，如有问题可联系订单客服。",
  COMPLETED: "订单已完成，仍可从订单服务中查看售后操作。",
  CANCELLED: "订单已取消，需要购买时可重新选购。",
  REFUNDED: "订单已退款，可在售后记录中查看处理结果。",
  PARTIALLY_REFUNDED: "订单已部分退款，剩余可退金额以订单服务为准。",
};

export function OrderProgress({ order }: { order: Order }) {
  const active = STAGES.findIndex((stage) => stage.state === order.status);
  return <div className="af-order-progress"><div className="af-order-progress-current"><MallStatus value={order.status} />
    <p>{ORDER_GUIDANCE[order.status] ?? "订单状态已更新，可刷新获取最新进度。"}</p></div>
    {active >= 0 && <ol aria-label="订单进度">{STAGES.map((stage, index) => <li key={stage.state}
      aria-current={index === active ? "step" : undefined} className={index <= active ? "reached" : undefined}>
      <span>{stage.label}</span>
    </li>)}</ol>}
  </div>;
}

export function OrderItems({ order }: { order: Order }) {
  if (!order.items?.length) return null;
  return <section className="af-order-items"><h3>商品明细</h3><ul>{order.items.map((item) => <li key={item.id}>
    <div><strong>{item.title_snapshot}</strong><span>{money(item.price_cents, order.currency)} × {item.qty} 件</span></div>
    <strong className="af-order-amount">{money(item.total_cents, order.currency)}</strong>
  </li>)}</ul></section>;
}
