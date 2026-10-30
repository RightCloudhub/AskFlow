import { useState } from "react";
import { Space, Tabs } from "antd";
import { ActionForm, type Field, type Row } from "./shared";
import { write } from "./client";
import { StepUp } from "./Verification";

type Operation = { title: string; permission: string; path: string; method?: string; purpose?: string; fields: Field[] };
const text = (name: string, label: string): Field => ({ name, label });
const number = (name: string, label: string): Field => ({ name, label, kind: "number" });
const boolean = (name: string, label: string): Field => ({ name, label, kind: "boolean" });
const version = number("expected_version", "当前版本");
const OPERATIONS: Record<string, Operation[]> = {
  account: [
    { title: "账号启用或禁用", permission: "user:manage", path: "/account/:id/state",
      fields: [text("id", "用户编号"), boolean("active", "启用账号")] },
    { title: "申请重置二步验证", permission: "user:manage", path: "/account/:id/mfa-reset", purpose: "mfa_reset_request",
      fields: [text("id", "用户编号"), text("reason", "申请原因")] },
    { title: "复核二步验证重置", permission: "user:manage", path: "/account/mfa-resets/:id/approve", purpose: "mfa_reset_approve",
      fields: [text("id", "申请编号"), version, boolean("approved", "批准此申请")] },
  ],
  catalog: [
    { title: "新增类目", permission: "catalog:write", path: "/catalog/categories", fields: [text("name", "名称"), text("slug", "英文标识")] },
    { title: "新增商品", permission: "catalog:write", path: "/catalog/products", fields: [text("title", "名称"), text("description", "描述")] },
    { title: "修改商品", permission: "catalog:write", path: "/catalog/products/:id", method: "PUT", fields: [text("id", "商品编号"), version, text("title", "名称"), text("description", "描述"), { ...text("images", "上传后的图片名称，逗号分隔"), required: false }] },
    { title: "新增规格", permission: "catalog:write", path: "/catalog/skus", fields: [text("spu_id", "商品编号"), text("code", "SKU 编码"), text("title", "名称"), number("sale_cents", "售价（分）"), number("original_cents", "原价（分）")] },
    { title: "商品上下架", permission: "catalog:write", path: "/catalog/products/:id/status", method: "PATCH", fields: [text("id", "商品编号"), version, text("status", "状态 active / inactive")] },
    { title: "规格上下架", permission: "catalog:write", path: "/catalog/skus/:id/status", method: "PATCH", fields: [text("id", "规格编号"), version, text("status", "状态 active / inactive")] },
    { title: "更新价格", permission: "catalog:write", path: "/catalog/skus/:id/price", method: "PUT", fields: [text("id", "规格编号"), version, number("sale_cents", "售价（分）"), number("original_cents", "原价（分）"), { ...number("activity_cents", "活动价（分，可留空）"), required: false }] },
  ],
  inventory: [
    { title: "库存入库", permission: "inventory:write", path: "/inventory/:id/replenish", fields: [text("id", "SKU 编号"), version, number("quantity", "入库数量")] },
    { title: "新增秒杀", permission: "inventory:write", path: "/inventory/flash-sales", fields: [text("name", "活动名称"), text("sku_id", "SKU 编号"),
      text("starts_at", "开始时间（含时区 ISO 8601）"), text("ends_at", "结束时间（含时区 ISO 8601）"), number("stock", "活动库存"), number("price_cents", "价格（分）")] },
  ],
  order: [
    { title: "发货与履约", permission: "order:write", path: "/order/:id/transition", fields: [text("id", "订单号"), version, text("status", "SHIPPED / DELIVERED / COMPLETED"), text("tracking_number", "物流单号")] },
    { title: "退款审核", permission: "order:refund", path: "/order/refunds/:id/review", fields: [text("id", "退款编号"), version, boolean("approved", "批准退款")] },
  ],
  wallet: [
    { title: "发起调账", permission: "wallet:adjust", path: "/wallet/adjustments", purpose: "wallet_adjust", fields: [text("user_id", "用户编号"), number("amount_cents", "调整额（分，可负）"), text("reason", "原因")] },
    { title: "第二人复核", permission: "wallet:approve", path: "/wallet/adjustments/:id/approve", purpose: "wallet_approve", fields: [text("id", "调账编号"), version, boolean("approved", "批准调账")] },
    { title: "申请冲正", permission: "wallet:adjust", path: "/wallet/reversals", purpose: "wallet_reversal", fields: [text("journal_id", "原分录编号"), text("reason", "冲正原因")] },
    { title: "复核冲正", permission: "wallet:approve", path: "/wallet/reversals/:id/approve", purpose: "wallet_approve", fields: [text("id", "冲正申请编号"), version, boolean("approved", "批准冲正")] },
    { title: "对账差异复核", permission: "finance:reconcile", path: "/wallet/differences/:id/review", fields: [text("id", "差异编号"), version, text("reference", "处置凭证编号"), text("reason", "复核说明")] },
    { title: "手工对账", permission: "finance:reconcile", path: "/wallet/reconciliation", fields: [] },
  ],
  referral: [{ title: "风控复核", permission: "risk:review", path: "/referral/:id/review", fields: [text("id", "风控事件编号"), version, boolean("approved", "批准放行"), text("note", "复核说明")] }],
  notify: [{ title: "保存通知模板", permission: "notify:write", path: "/notify/templates", fields: [text("event_type", "事件名"), text("locale", "语言 zh-CN / en-US"), text("subject", "主题"), text("body", "正文模板"), { ...text("channels", "外发渠道 email,sms（留空仅站内信）"), required: false }, version] }],
  settings: [
    { title: "保存配置", permission: "settings:write", path: "/settings/:id", method: "PUT", fields: [text("id", "配置键"), version, number("value", "配置值")] },
    { title: "授予角色", permission: "rbac:write", path: "/roles/grant", fields: [text("user_id", "用户编号"), text("role", "角色代码")] },
    { title: "撤销角色", permission: "rbac:write", path: "/roles/grants/:user_id/:role_id", method: "DELETE", fields: [text("user_id", "用户编号"), text("role_id", "角色编号")] },
    { title: "新增角色", permission: "rbac:write", path: "/roles", fields: [text("code", "角色代码"), text("name", "角色名称")] },
    { title: "角色权限", permission: "rbac:write", path: "/roles/:id/permissions", method: "PUT", fields: [text("id", "角色编号"), version, text("permissions", "权限代码，逗号分隔")] },
    { title: "回滚配置", permission: "settings:write", path: "/settings/:id/rollback",
      fields: [text("id", "配置键"), version, number("source_version", "回滚到的版本")] },
  ],
};

function OperationForm({ operation, reload }: { operation: Operation; reload: () => Promise<void> }) {
  const [token, setToken] = useState("");
  async function submit(values: Row) {
    const body = { ...values };
    if ("permissions" in body) body.permissions = String(body.permissions).split(",").map((value) => value.trim()).filter(Boolean);
    if ("channels" in body) body.channels = String(body.channels ?? "").split(",").map((value) => value.trim()).filter(Boolean);
    if ("images" in body) body.images = String(body.images ?? "").split(",").map((value) => value.trim()).filter(Boolean);
    if (operation.purpose) body.step_up_token = token;
    const path = operation.path.replace(/:([a-z_]+)/g, (_match, key: string) => {
      const value = body[key]; delete body[key]; return encodeURIComponent(String(value ?? ""));
    });
    await write("/api/v1/admin/mall" + path, body, { method: operation.method });
    await reload();
  }
  return <Space direction="vertical" style={{ width: "100%" }}>
    {operation.purpose && <StepUp purpose={operation.purpose} onToken={setToken} />}
    {(!operation.purpose || token) && <ActionForm label={operation.title} fields={operation.fields} submit={submit} />}
  </Space>;
}

export function AdminForms({ module, permissions, reload }: { module: string; permissions: string[]; reload: () => Promise<void> }) {
  return <Tabs items={(OPERATIONS[module] ?? []).filter((operation) => permissions.includes(operation.permission)).map((operation) => ({
    key: operation.title, label: operation.title, children: <OperationForm operation={operation} reload={reload} />,
  }))} />;
}

export function hasAdminOperations(module: string, permissions: string[]) {
  return (OPERATIONS[module] ?? []).some((operation) => permissions.includes(operation.permission));
}
