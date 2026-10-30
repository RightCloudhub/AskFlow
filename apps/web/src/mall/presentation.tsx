import type { ReactNode } from "react";
import { Tag } from "antd";

type PageProps = { title: string; description?: string; actions?: ReactNode; children: ReactNode; className?: string };

export function MallPage({ title, description, actions, children, className = "" }: PageProps) {
  return <div className={`af-mall-page ${className}`}>
    <header className="af-mall-page-head">
      <div><h1>{title}</h1>{description && <p>{description}</p>}</div>
      {actions && <div className="af-mall-page-actions">{actions}</div>}
    </header>
    <div className="af-mall-page-body">{children}</div>
  </div>;
}

export function MallPanel({ title, description, actions, children, className = "" }: PageProps) {
  return <section className={`af-mall-panel ${className}`}>
    <header className="af-mall-panel-head">
      <div><h2>{title}</h2>{description && <p>{description}</p>}</div>
      {actions}
    </header>
    {children}
  </section>;
}

const STATUS_LABELS: Record<string, string> = {
  PENDING_PAYMENT: "待支付", PAID: "已支付", SHIPPED: "已发货", DELIVERED: "已送达",
  COMPLETED: "已完成", CANCELLED: "已取消", CANCELED: "已取消", CLOSED: "已关闭",
  REFUNDED: "已退款", PARTIALLY_REFUNDED: "部分退款", PENDING: "待处理", APPROVED: "已批准",
  REJECTED: "未通过", SUCCEEDED: "已成功", FAILED: "失败", PROCESSING: "处理中",
  FROZEN: "冻结中", SETTLED: "已结算", ISSUED: "已发放", REVIEW: "审核中",
};
const ATTENTION = new Set(["PENDING_PAYMENT", "PENDING", "REVIEW"]);
const NEGATIVE = new Set(["FAILED", "REJECTED"]);
const POSITIVE = new Set(["COMPLETED", "APPROVED", "SUCCEEDED", "SETTLED", "ISSUED", "DELIVERED"]);
const PROCESSING = new Set(["PAID", "SHIPPED", "PROCESSING"]);

function statusTone(status: string) {
  if (NEGATIVE.has(status)) return "danger";
  if (ATTENTION.has(status)) return "warning";
  if (POSITIVE.has(status)) return "success";
  return PROCESSING.has(status) ? "processing" : "neutral";
}

export function MallStatus({ value }: { value: unknown }) {
  const status = String(value ?? "").toUpperCase();
  const tone = statusTone(status);
  return <Tag className={`af-mall-status af-mall-status--${tone}`}>{STATUS_LABELS[status] ?? (status || "—")}</Tag>;
}

export function MallEmpty({ title, children }: { title: string; children?: ReactNode }) {
  return <div className="af-mall-empty"><p>{title}</p>{children}</div>;
}

export function formatDate(value: unknown) {
  if (!value) return "—";
  const date = new Date(String(value));
  return Number.isNaN(date.getTime()) ? "—" : date.toLocaleString("zh-CN", {
    month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit",
  });
}
