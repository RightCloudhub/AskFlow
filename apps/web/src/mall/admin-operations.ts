import type { Field } from "./form-fields";
import { PERMISSION_OPTIONS } from "./permission-options.ts";
import { NOTIFICATION_EVENTS } from "./notification-options.ts";

export type Operation = { title: string; permission: string; path: string; method?: string; purpose?: string; fields: Field[]; editExisting?: boolean };
const text = (name: string, label: string): Field => ({ name, label });
const number = (name: string, label: string): Field => ({ name,
  label: label.replace("（分，可负）", "（元，可负）").replace("（分，可留空）", "（元，可留空）").replace("（分）", "（元）"),
  kind: name.endsWith("_cents") ? "money" : "number", min: name === "amount_cents" ? undefined : 0 });
const boolean = (name: string, label: string): Field => ({ name, label, kind: "boolean" });
const version = number("expected_version", "当前版本");
const TEMPLATE_FIELDS: Field[] = [
  { name: "event_type", label: "通知事件", kind: "suggest", options: NOTIFICATION_EVENTS, step: "通知对象" },
  { name: "locale", label: "语言", kind: "select", step: "通知对象", options: [
    { value: "zh-CN", label: "简体中文" }, { value: "en-US", label: "英语" }] },
  { ...text("subject", "主题"), step: "通知内容" },
  { ...text("body", "正文模板"), kind: "textarea", step: "通知内容" },
  { name: "channels", label: "外发渠道", kind: "multiselect", required: false, step: "发送设置",
    hint: "未选择外发渠道时，仅发送站内信。", options: [{ value: "email", label: "电子邮件" }, { value: "sms", label: "短信" }] },
  { ...version, hidden: true },
];
export const OPERATIONS: Record<string, Operation[]> = {
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
    { title: "新增商品", permission: "catalog:write", path: "/catalog/products", fields: [text("title", "名称"),
      { ...text("description", "描述"), kind: "textarea", required: false }] },
    { title: "修改商品", permission: "catalog:write", path: "/catalog/products/:id", method: "PUT", fields: [text("id", "商品编号"), version, text("title", "名称"), { ...text("description", "描述"), kind: "textarea" }, { ...text("images", "上传后的图片名称，逗号分隔"), required: false }] },
    { title: "新增规格", permission: "catalog:write", path: "/catalog/skus", fields: [text("spu_id", "商品编号"), text("code", "SKU 编码"), text("title", "名称"), number("sale_cents", "售价（分）"), number("original_cents", "原价（分）")] },
    { title: "商品上下架", permission: "catalog:write", path: "/catalog/products/:id/status", method: "PATCH", fields: [text("id", "商品编号"), version, visibility()] },
    { title: "规格上下架", permission: "catalog:write", path: "/catalog/skus/:id/status", method: "PATCH", fields: [text("id", "规格编号"), version, visibility()] },
    { title: "更新价格", permission: "catalog:write", path: "/catalog/skus/:id/price", method: "PUT", fields: [text("id", "规格编号"), version, number("sale_cents", "售价（分）"), number("original_cents", "原价（分）"), { ...number("activity_cents", "活动价（分，可留空）"), required: false }] },
  ],
  inventory: [
    { title: "库存入库", permission: "inventory:write", path: "/inventory/:id/replenish", fields: [text("id", "SKU 编号"), version,
      { ...number("quantity", "入库数量"), min: 1 }] },
    { title: "新增秒杀", permission: "inventory:write", path: "/inventory/flash-sales", fields: [text("name", "活动名称"), text("sku_id", "SKU 编号"),
      { name: "starts_at", label: "开始时间", kind: "datetime", step: "活动时间" },
      { name: "ends_at", label: "结束时间", kind: "datetime", step: "活动时间", rules: [({ getFieldValue }) => ({
        validator: (_, value) => !value || !getFieldValue("starts_at") || Date.parse(value) > Date.parse(getFieldValue("starts_at"))
          ? Promise.resolve() : Promise.reject(new Error("结束时间须晚于开始时间。")),
      })] }, { ...number("stock", "活动库存"), step: "库存与价格", min: 1 },
      { ...number("price_cents", "价格（分）"), step: "库存与价格" }] },
  ],
  order: [
    { title: "发货与履约", permission: "order:write", path: "/order/:id/transition", fields: [text("id", "订单号"), version,
      { name: "status", label: "履约状态", kind: "select", options: [
        { value: "SHIPPED", label: "已发货" }, { value: "DELIVERED", label: "已送达" }, { value: "COMPLETED", label: "已完成" }] },
      { ...text("tracking_number", "物流单号"), required: false }] },
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
  notify: [
    { title: "新增通知模板", permission: "notify:write", path: "/notify/templates", fields: TEMPLATE_FIELDS },
    { title: "编辑通知模板", permission: "notify:write", path: "/notify/templates", fields: TEMPLATE_FIELDS, editExisting: true },
  ],
  settings: [
    { title: "保存配置", permission: "settings:write", path: "/settings/:id", method: "PUT", fields: [text("id", "配置键"), version, number("value", "配置值")] },
    { title: "回滚配置", permission: "settings:write", path: "/settings/:id/rollback",
      fields: [text("id", "配置键"), version, number("source_version", "回滚到的版本")] },
  ],
  roles: [
    { title: "授予角色", permission: "rbac:write", path: "/roles/grant", fields: [text("user_id", "用户编号"), text("role", "角色代码")] },
    { title: "撤销角色", permission: "rbac:write", path: "/roles/grants/:user_id/:role_id", method: "DELETE", fields: [text("user_id", "用户编号"), text("role_id", "角色编号")] },
    { title: "新增角色", permission: "rbac:write", path: "/roles", fields: [text("code", "角色代码"), text("name", "角色名称")] },
    { title: "角色权限", permission: "rbac:write", path: "/roles/:id/permissions", method: "PUT", fields: [text("id", "角色编号"), version,
      { name: "permissions", label: "允许访问的业务", kind: "multiselect", required: false, options: PERMISSION_OPTIONS }] },
  ],
};

function visibility(): Field {
  return { name: "status", label: "上架状态", kind: "select", options: [
    { value: "active", label: "上架" }, { value: "inactive", label: "下架" }] };
}
