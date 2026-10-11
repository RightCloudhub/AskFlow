/** Chinese display labels for admin metrics & status values. */

export const METRIC_LABELS: Record<string, string> = {
  messages: "消息总量",
  tickets_open: "未结工单",
  handoffs_queued: "排队接管",
  gaps_open: "开放缺口",
  thumbs_down: "差评数",
  thumbs_up: "好评数",
  thumbs_down_rate: "差评率",
  sla_breached: "SLA 违约",
  handoff_timeouts: "接管超时",
  notifications: "通知次数",
  cost_estimated_usd: "预估成本 (USD)",
  agent_runs: "Agent 运行",
  refused_runs: "拒答次数",
  refuse_rate: "拒答率",
  handoffs: "接管会话",
  quality_score_avg: "平均质检分",
  prompt_tokens: "输入 Token",
  completion_tokens: "输出 Token",
  estimated_usd: "预估费用",
  calls: "调用次数",
};

export const STATUS_LABELS: Record<string, string> = {
  pending: "待处理",
  processing: "处理中",
  resolved: "已解决",
  closed: "已关闭",
  open: "开放",
  dismissed: "已忽略",
  draft: "草稿",
  approved: "已通过",
  rejected: "已拒绝",
  queued: "排队中",
  claimed: "已认领",
  returned: "已交还",
  timed_out: "已超时",
  active: "启用",
  disabled: "已禁用",
  enabled: "已启用",
  indexed: "已索引",
  indexing: "索引中",
  failed: "失败",
  warning: "预警",
  breached: "违约",
  ok: "正常",
  on: "开启",
  off: "关闭",
  planned: "规划中",
  measuring: "度量中",
  shipped: "已上线",
  admin: "管理员",
  agent: "座席",
  user: "用户",
  staff: "员工",
};

export const TONE_BY_STATUS: Record<
  string,
  "ok" | "warn" | "danger" | "info" | "neutral"
> = {
  pending: "warn",
  processing: "info",
  resolved: "ok",
  closed: "neutral",
  open: "warn",
  dismissed: "neutral",
  draft: "info",
  approved: "ok",
  rejected: "danger",
  queued: "warn",
  claimed: "info",
  returned: "ok",
  timed_out: "danger",
  active: "ok",
  disabled: "danger",
  warning: "warn",
  breached: "danger",
  ok: "ok",
  failed: "danger",
  indexing: "info",
  indexed: "ok",
};

export function labelMetric(key: string): string {
  return METRIC_LABELS[key] ?? key;
}

export function labelStatus(value: string | null | undefined): string {
  if (!value) return "—";
  return STATUS_LABELS[value] ?? value;
}

export function statusTone(
  value: string | null | undefined,
): "ok" | "warn" | "danger" | "info" | "neutral" {
  if (!value) return "neutral";
  return TONE_BY_STATUS[value] ?? "neutral";
}

export function formatNumber(value: number, digits = 0): string {
  if (!Number.isFinite(value)) return "—";
  if (Math.abs(value) >= 1_000_000) return `${(value / 1_000_000).toFixed(2)}M`;
  if (Math.abs(value) >= 10_000) return `${(value / 1_000).toFixed(1)}k`;
  if (Number.isInteger(value) && digits === 0)
    return value.toLocaleString("zh-CN");
  return value.toLocaleString("zh-CN", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

export function formatUsd(value: number): string {
  if (!Number.isFinite(value)) return "—";
  return `$${value.toLocaleString("zh-CN", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 4,
  })}`;
}

export function formatRate(value: number): string {
  if (!Number.isFinite(value)) return "—";
  return `${(value * 100).toFixed(1)}%`;
}

export function purposeLabel(purpose: string): string {
  const map: Record<string, string> = {
    intent: "意图识别",
    rewrite: "查询改写",
    answer: "答案生成",
    tool: "工具调用",
    classify: "分类",
    embedding: "向量嵌入",
    summary: "会话摘要",
    reasoning: "扩展推理",
    intent_classify: "意图识别",
    query_rewrite: "查询改写",
    rag_generate: "答案生成",
    handoff_summary: "转人工摘要",
    history_summary: "会话摘要",
    qc_score: "质检评分",
  };
  return map[purpose] ?? purpose;
}

export const TICKET_TYPE_LABELS: Record<string, string> = {
  after_sales: "售后",
  invoice: "发票",
  account: "账户",
  logistics: "物流",
  refund: "退款",
  complaint: "投诉",
  fault_report: "故障报修",
  order_query: "订单查询",
  user_created: "用户提交",
  auto_created: "系统创建",
  agent_created: "智能助手创建",
  handoff: "转人工",
  sla: "SLA 升级",
  handoff_timeout: "接管超时",
};

export function ticketTypeLabel(type?: string | null): string {
  if (!type) return "—";
  return TICKET_TYPE_LABELS[type] ?? type;
}

export const INTENT_LABELS: Record<string, string> = {
  faq: "常见问题",
  product: "产品咨询",
  order_query: "订单查询",
  fault_report: "故障报修",
  complaint: "投诉",
  handoff: "转人工",
  out_of_scope: "超出范围",
};

export function intentLabel(intent?: string | null): string {
  if (!intent) return "—";
  return INTENT_LABELS[intent] ?? intent;
}

/** Why a question became a knowledge gap, and what to do about it. */
export const GAP_REASON_LABELS: Record<string, { label: string; hint: string }> = {
  zero_hit: { label: "无命中", hint: "知识库没有相关内容，建议新增文档" },
  weak_evidence: {
    label: "证据不足",
    hint: "有相关内容但匹配度低，建议补充说法或同义词",
  },
};

export function gapReason(reason?: string | null): { label: string; hint: string } {
  if (reason && GAP_REASON_LABELS[reason]) return GAP_REASON_LABELS[reason];
  return { label: "未记录原因", hint: "历史数据，未保存拒答原因" };
}

/** "3 分钟" / "2 小时 5 分" / "1 天 3 小时" since an ISO timestamp. */
export function formatWaiting(since?: string | null, now: number = Date.now()): string {
  if (!since) return "—";
  // SQLite returns naive UTC timestamps ("2026-10-11T13:07:47"); without a zone the
  // browser would read them as local time and be off by the UTC offset.
  const iso = /[zZ]|[+-]\d{2}:?\d{2}$/.test(since) ? since : `${since}Z`;
  const minutes = Math.max(0, Math.floor((now - new Date(iso).getTime()) / 60_000));
  if (minutes < 60) return `${minutes} 分钟`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} 小时 ${minutes % 60} 分`;
  return `${Math.floor(hours / 24)} 天 ${hours % 24} 小时`;
}
