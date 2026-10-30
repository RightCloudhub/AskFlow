import { CatalogUpload } from "./CatalogUpload";
import { FinanceRecords, Records } from "./AdminRecords";
import { AdminForms, hasAdminOperations } from "./AdminForms";
import { MallPanel } from "./presentation";

type AdminWorkspaceProps = { module: string; revision: number; permissions: string[]; reload: () => Promise<void> };
const RESOURCE: Record<string, string> = {
  catalog: "/catalog", order: "/order", payment: "/payment", wallet: "/wallet/accounts",
  referral: "/referral", notify: "/notify/deliveries", support: "/support", settings: "/settings",
  account: "/account", inventory: "/inventory",
};

function BusinessRecords({ module, revision, permissions }: AdminWorkspaceProps) {
  if (module === "wallet") return <FinanceRecords key={revision} permissions={permissions} />;
  if (!RESOURCE[module]) return null;
  return <Records key={`${module}:${revision}`} path={RESOURCE[module]} />;
}

export function AdminResources(props: AdminWorkspaceProps) {
  const operations = hasAdminOperations(props.module, props.permissions);
  const aside = operations || props.module === "catalog";
  return <div className={aside ? "af-mall-admin-grid" : "af-mall-admin-stack"}>
    <div className="af-mall-admin-stack"><MallPanel title="业务记录"><BusinessRecords {...props} /></MallPanel>
      {props.module === "account" && <MallPanel title="二步验证重置申请"><Records key={props.revision} path="/account/mfa-resets" /></MallPanel>}
      {props.module === "catalog" && <MallPanel title="商品规格"><Records key={props.revision} path="/catalog/skus" /></MallPanel>}
      {props.module === "settings" && props.permissions.includes("rbac:write") && <MallPanel title="角色记录"><Records key={props.revision} path="/roles" /></MallPanel>}
    </div>{aside && <aside className="af-mall-admin-operations">
      {operations && <MallPanel title="管理操作"><AdminForms module={props.module} permissions={props.permissions} reload={props.reload} /></MallPanel>}
      {props.module === "catalog" && <MallPanel title="商品图片"><CatalogUpload /></MallPanel>}
    </aside>}
  </div>;
}
