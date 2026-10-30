import { useState } from "react";
import { Button, Popconfirm } from "antd";
import { Link } from "react-router-dom";
import { useFeatures } from "../plugins/features";
import { ActionFeedback, useActionFeedback } from "../components/common/action-feedback";
import { write } from "./client";
import { OrderPaymentFlow } from "./OrderPaymentFlow";
import { OrderRefundFlow } from "./OrderRefundFlow";
import { OrderCancelFlow } from "./OrderCancelFlow";
import { refundableAmount, REFUNDABLE_STATUSES, type Order, type OrderFlowProps } from "./order-types";

export type { Order } from "./order-types";
type Action = "payment" | "refunds" | "cancel";
type ActionsProps = Omit<OrderFlowProps, "onExit">;

function OrderServiceChoices({ order, reload, choose }: ActionsProps & { choose: (action: Action) => void }) {
  const { enabled } = useFeatures();
  const feedback = useActionFeedback();
  return <div className="af-flow-success">
    <div className="af-work-actions">
      {order.status === "PENDING_PAYMENT" && <>
        {enabled("mall_payment") && <Button type="primary" onClick={() => choose("payment")}>去支付</Button>}
        <Button onClick={() => choose("cancel")}>取消订单</Button>
      </>}
      {enabled("mall_payment") && REFUNDABLE_STATUSES.has(order.status) && <Button disabled={feedback.busy || !refundableAmount(order)}
        onClick={() => choose("refunds")}>申请退款</Button>}
      {order.status === "SHIPPED" && <Popconfirm title="已收到并核对商品？" okText="确认收货" cancelText="稍后确认"
        disabled={feedback.busy} onConfirm={() => feedback.run(async () => {
          await write(`/order/orders/${encodeURIComponent(order.id)}/received`, { expected_version: order.version });
          feedback.succeed("已确认收货。");
          await reload();
        })}><Button loading={feedback.busy}>确认收货</Button></Popconfirm>}
    </div>
    <ActionFeedback state={feedback} />
  </div>;
}

function OrderServices(props: ActionsProps) {
  const { enabled } = useFeatures();
  const [action, setAction] = useState<Action>();
  const flowProps = { ...props, onExit: () => setAction(undefined) };
  return <div className="af-order-actions">
    {!action && <OrderServiceChoices {...props} choose={setAction} />}
    {action === "payment" && <OrderPaymentFlow {...flowProps} />}
    {action === "refunds" && <OrderRefundFlow {...flowProps} />}
    {action === "cancel" && <OrderCancelFlow {...flowProps} />}
    {enabled("mall_support") && <Link to={`/shop/messages?order_id=${encodeURIComponent(props.order.id)}`}>联系订单客服</Link>}
  </div>;
}

export function OrderActions(props: { order: Order; reload: () => Promise<void> }) {
  return <OrderServices key={props.order.id} {...props} />;
}
