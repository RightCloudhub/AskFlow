import { useCallback } from "react";
import { mall } from "./client";
import { useLoad, type Page, type Row } from "./shared";
import { useFeatures } from "../plugins/features";
import { Tabs } from "antd";
import { MallPage } from "./presentation";
import { useCursor } from "./query-view";
import { Notices, ServiceRecords, SupportRequest } from "./message-parts";

function SupportWorkspace() {
  const paging = useCursor();
  const query = useLoad(useCallback(() => mall<Page<Row>>(`/support?cursor=${encodeURIComponent(paging.cursor)}`), [paging.cursor]));
  return <div className="af-support-workspace"><ServiceRecords query={query} paging={paging} /><SupportRequest reload={query.reload} /></div>;
}

export function Messages() {
  const { enabled } = useFeatures();
  const items = [
    ...(enabled("mall_support") ? [{ key: "support", label: "客服跟进", children: <SupportWorkspace /> }] : []),
    ...(enabled("mall_notify") ? [{ key: "notices", label: "业务通知", children: <Notices /> }] : []),
  ];
  return <MallPage title="消息与客服" description="订单与售后有问题，在这里继续跟进。" className="af-messages-page">
    <Tabs items={items} />
  </MallPage>;
}
