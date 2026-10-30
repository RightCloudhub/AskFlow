import type { ColumnsType } from "antd/es/table";
import { money } from "./client";
import type { Row } from "./shared";
import { MallStatus } from "./presentation";

const LABELS: Record<string, string> = {
  id: "编号", key: "配置键", title: "名称", name: "名称", code: "代码", username: "用户名", nickname: "昵称",
  email: "邮箱", phone: "手机号", status: "状态", active: "已启用", is_active: "已启用", version: "版本",
  created_at: "创建时间", updated_at: "更新时间", user_id: "用户编号", order_id: "订单编号",
  total_cents: "金额", amount_cents: "金额", available_cents: "可用余额", frozen_cents: "冻结金额",
  sale_cents: "售价", original_cents: "原价", activity_cents: "活动价", price_cents: "价格", currency: "币种",
  spu_id: "商品编号", sku_id: "规格编号", quantity: "数量", stock: "库存", reserved: "已预留",
  description: "说明", images: "图片", attributes: "属性", category_id: "类目编号", reason: "原因",
  permissions: "权限", role_id: "角色编号", role: "角色", event_type: "事件", channel: "渠道",
  subject: "主题", body: "正文", locale: "语言", target: "目标", destination: "去向", reference: "凭证编号",
  implementation: "当前实现", multi_instance_safe: "多实例安全", tracking_number: "物流单号",
};
const IDENTITIES = new Set(["id", "title", "name", "username", "description", "key"]);

function renderCell(key: string, value: unknown, row: Row) {
  if (value == null) return "—";
  if (key === "status") return <MallStatus value={value} />;
  if (key.endsWith("_cents")) return money(Number(value), String(row.currency ?? "CNY"));
  if (typeof value === "boolean") return value ? "是" : "否";
  if (typeof value === "number") return value.toLocaleString("zh-CN");
  if (typeof value === "object") return <pre>{JSON.stringify(value, null, 2)}</pre>;
  return String(value);
}

export function recordColumns(rows: Row[]): ColumnsType<Row> {
  return Object.keys(rows[0] ?? {}).map((key) => ({
    title: LABELS[key] ?? key, key, dataIndex: key,
    className: typeof rows[0]?.[key] === "number" ? "af-numeric-cell" : IDENTITIES.has(key) ? "af-record-identity" : undefined,
    render: (value: unknown, row: Row) => renderCell(key, value, row),
  }));
}
