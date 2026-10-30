import { useCallback, useState } from "react";
import { Button, Descriptions, List } from "antd";
import { Link, useSearchParams } from "react-router-dom";
import { mall, money } from "./client";
import { Feedback, useLoad, type Page, type Row } from "./shared";
import { useFeatures } from "../plugins/features";
import { MallPage, MallPanel, MallStatus } from "./presentation";

export function AfterSales() {
  const { enabled } = useFeatures();
  const [cursor, setCursor] = useState("");
  const load = useCallback(() => mall<Page<Row>>(`/order/refunds?cursor=${encodeURIComponent(cursor)}`), [cursor]);
  const query = useLoad(load);
  return <MallPage title="我的售后" description="跟进退款申请，查看关联订单与处理状态。" actions={<Link to="/shop/orders">查看订单</Link>}>
    <Feedback {...query} /><MallPanel title="售后记录">
      <List className="af-order-list" dataSource={query.data?.items} locale={{ emptyText: "暂无售后申请。需要退款时，可从订单详情发起。" }}
        renderItem={(row) => <List.Item><div className="af-order-identity">
          <Link to={`/shop/orders/${row.order_id}`}>查看关联订单</Link>
          {enabled("mall_support") && <Link to={`/shop/messages?refund_id=${row.id}`}>联系售后客服</Link>}
        </div><MallStatus value={row.status} /><strong className="af-order-amount">
          {money(Number(row.amount_cents), String(row.currency ?? "CNY"))}
        </strong></List.Item>} />
      {query.data?.next_cursor && <div className="af-mall-pagination">
        <Button onClick={() => setCursor(query.data!.next_cursor!)}>下一页售后</Button>
      </div>}
    </MallPanel>
  </MallPage>;
}

export function PaymentResult() {
  const [params] = useSearchParams();
  const id = params.get("payment_id");
  const load = useCallback(() => id ? mall<Row>(`/payment/${encodeURIComponent(id)}`) : Promise.resolve({}), [id]);
  const query = useLoad<Row>(load);
  return <MallPage title="支付结果" description="支付状态以订单记录为准，可刷新获取最新结果。" actions={<Link to="/shop/orders">返回订单</Link>}>
    <Feedback {...query} /><MallPanel title="支付信息">
      <Descriptions column={1} items={[
        { key: "status", label: "支付状态", children: id ? <MallStatus value={query.data?.status} /> : "请选择支付单" },
        { key: "amount", label: "支付金额", children: query.data?.amount_cents == null ? "—" : money(Number(query.data.amount_cents), String(query.data.currency ?? "CNY")) },
      ]} /><Button loading={query.loading} disabled={!id} onClick={() => { void query.reload(); }}>刷新结果</Button>
    </MallPanel>
  </MallPage>;
}
