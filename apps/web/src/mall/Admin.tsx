import { useCallback, useState } from "react";
import { Table } from "antd";
import { useLocation } from "react-router-dom";
import { mall } from "./client";
import { Feedback, useLoad, type Row } from "./shared";
import { MALL_ADMIN } from "./admin-registry";
import { useMallPermissions } from "./permissions";
import { MallDashboard } from "./mall-dashboard";
import { MallEmpty, MallPage, MallPanel } from "./presentation";
import { AdminResources } from "./admin-resources";
import { DESIGN } from "../design/tokens";
import "../styles/mall.css";

export function MallAdmin() {
  const [revision, setRevision] = useState(0);
  const module = useLocation().pathname.split("/").slice(-1)[0] ?? "settings";
  const grants = useMallPermissions();
  const entry = MALL_ADMIN.find((item) => item.module === module);
  const allowed = grants.permissions.includes(entry?.permission ?? "");
  if (module === "dashboard") return <MallDashboard />;
  if (!allowed) return <MallPage title={entry?.label ?? "商城管理"}><Feedback {...grants} />
    {!grants.loading && <MallEmpty title="此操作需要相应商城权限。" />}</MallPage>;
  return <MallPage title={entry?.label ?? "商城管理"} description="核对业务记录，再执行对应的管理操作。" className="af-mall-admin">
    <AdminResources module={module} revision={revision} permissions={grants.permissions}
      reload={async () => setRevision((value) => value + 1)} />
  </MallPage>;
}

export function InfraPage() {
  const loader = useCallback(() => mall<{ preset: string; ports: Row[] }>("/api/v1/admin/infra"), []);
  const query = useLoad(loader);
  return <MallPage title="基础设施" description={query.data?.preset ? `当前部署方案：${query.data.preset}` : "查看能力实现与多实例支持情况。"} className="af-mall-admin">
    <Feedback {...query} /><MallPanel title="能力实现">
      <Table rowKey="port" dataSource={query.data?.ports} pagination={false} sticky={{ offsetHeader: DESIGN.header }} columns={[
        { title: "能力", dataIndex: "port" }, { title: "当前实现", dataIndex: "implementation" },
        { title: "多实例安全", dataIndex: "multi_instance_safe", render: (value: boolean) => value ? "是" : "否" },
        { title: "说明", dataIndex: "description" },
      ]} scroll={{ x: "max-content" }} />
    </MallPanel>
  </MallPage>;
}
