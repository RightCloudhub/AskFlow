import { CatalogUpload } from "./CatalogUpload";
import { FinanceRecords, Records } from "./AdminRecords";
import { AdminForms, hasAdminOperations } from "./AdminForms";
import { MallEmpty, MallPanel } from "./presentation";

type AdminWorkspaceProps = { module: string; revision: number; permissions: string[]; reload: () => Promise<void> };
const RESOURCE: Record<string, string> = {
  catalog: "/catalog", order: "/order", payment: "/payment", wallet: "/wallet/accounts",
  referral: "/referral", notify: "/notify/deliveries", support: "/support", settings: "/settings",
  account: "/account", inventory: "/inventory", roles: "/roles",
};
const RELATED: Record<string, { title: string; path: string; permission?: string }> = {
  account: { title: "二步验证重置申请", path: "/account/mfa-resets" },
  catalog: { title: "商品规格", path: "/catalog/skus" },
  order: { title: "退款申请", path: "/order/refunds/pending", permission: "order:refund" },
  roles: { title: "已授予的角色", path: "/roles/grants" },
  notify: { title: "当前通知模板", path: "/notify/templates" },
};

function BusinessRecords({ module, revision, permissions }: AdminWorkspaceProps) {
  if (module === "wallet") return <FinanceRecords key={revision} permissions={permissions} />;
  if (module === "order" && !permissions.includes("order:read")) return <MallEmpty title="当前账号没有订单列表权限" />;
  if (!RESOURCE[module]) return null;
  return <Records key={`${module}:${revision}`} path={RESOURCE[module]} />;
}

function RelatedRecords({ module, revision, permissions }: AdminWorkspaceProps) {
  const entry = RELATED[module];
  if (!entry || (entry.permission && !permissions.includes(entry.permission))) return null;
  return <MallPanel title={entry.title}><Records key={revision} path={entry.path} /></MallPanel>;
}

export function AdminResources(props: AdminWorkspaceProps) {
  const operations = hasAdminOperations(props.module, props.permissions);
  const aside = operations || props.module === "catalog";
  return <div className={aside ? "af-mall-admin-grid" : "af-mall-admin-stack"}>
    <div className="af-mall-admin-stack"><MallPanel title="业务记录"><BusinessRecords {...props} /></MallPanel>
      <RelatedRecords {...props} />
    </div>{aside && <aside className="af-mall-admin-operations">
      {operations && <MallPanel title="管理操作"><AdminForms revision={props.revision} module={props.module} permissions={props.permissions} reload={props.reload} /></MallPanel>}
      {props.module === "catalog" && <MallPanel title="商品图片"><CatalogUpload /></MallPanel>}
    </aside>}
  </div>;
}
