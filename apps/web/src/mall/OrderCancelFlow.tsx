import { useState } from "react";
import { Alert, Button } from "antd";
import { FlowFrame } from "../components/common/FlowFrame";
import { ActionFeedback } from "../components/common/action-feedback";
import { money } from "./client";
import { useOrderCommand } from "./order-command";
import type { OrderFlowProps } from "./order-types";

const TITLES = ["核对订单", "确认取消"];
type CancelState = ReturnType<typeof useOrderCommand>;

function CancelReview({ order, current, command }: { order: OrderFlowProps["order"]; current: number; command: CancelState }) {
  return <div className="af-flow-success">
    <div className="af-form-review"><dl>
      <div><dt>订单号</dt><dd>{order.id}</dd></div>
      <div><dt>订单金额</dt><dd>{money(order.total_cents, order.currency)}</dd></div>
    </dl></div>
    <Alert type="warning" showIcon title={current === 0 ? "取消后无法继续支付此订单" : "确认取消这笔订单？"}
      description="取消后将释放占用库存；如需购买，请重新下单。" />
    {current > 0 && !command.pending && <p className="af-mall-note">确认信息已失效，请重新核对订单。</p>}
  </div>;
}

function CancelSubmit({ current, command, prepare }: { current: number; command: CancelState; prepare: () => Promise<void> }) {
  if (command.complete) return null;
  if (current > 0 && command.pending) return <Button type="primary" danger loading={command.busy} onClick={() => void command.submit()}>
    {command.awaitingResult ? "重试并获取结果" : "确认取消订单"}</Button>;
  return <Button type="primary" loading={command.busy} onClick={() => void prepare()}>{current === 0 ? "下一步" : "重新核对"}</Button>;
}

export function OrderCancelFlow(props: OrderFlowProps) {
  const [current, setCurrent] = useState(0);
  const command = useOrderCommand({ ...props, kind: "cancel" });
  const { order } = props;
  async function prepare() {
    const ready = await command.prepare(() => {
      if (order.status !== "PENDING_PAYMENT") throw new Error("订单状态已变化，请返回订单服务查看。");
      return { expected_version: order.version, reason: "customer_request" };
    });
    if (ready) setCurrent(1);
  }
  function back() {
    if (command.locked || command.complete) return;
    command.invalidate(); setCurrent(0);
  }
  return <FlowFrame titles={TITLES} current={current} title={command.complete ? "订单已取消" : undefined}
    onBack={back} busy={command.busy} backDisabled={command.complete || command.awaitingResult} focusOnMount>
    {command.complete ? <Alert type="success" showIcon title="订单已取消" /> : <CancelReview order={order} current={current} command={command} />}
    <ActionFeedback state={command.feedback} />
    {command.awaitingResult && !command.busy && <p className="af-mall-note">尚未收到处理结果。请重试原操作，确认结果后再继续。</p>}
    <div className="af-form-flow-actions">
      {current > 0 && !command.complete && <Button disabled={command.locked} onClick={back}>上一步</Button>}
      <Button disabled={command.locked} onClick={props.onExit}>返回订单服务</Button>
      <CancelSubmit current={current} command={command} prepare={prepare} />
    </div>
  </FlowFrame>;
}
