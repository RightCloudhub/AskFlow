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

export const TONE_BY_STATUS: Record<string, "ok" | "warn" | "danger" | "info" | "neutral"> = {
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
  value: string | null | undefined
): "ok" | "warn" | "danger" | "info" | "neutral" {
  if (!value) return "neutral";
  return TONE_BY_STATUS[value] ?? "neutral";
}

export function formatNumber(value: number, digits = 0): string {
  if (!Number.isFinite(value)) return "—";
  if (Math.abs(value) >= 1_000_000) return `${(value / 1_000_000).toFixed(2)}M`;
  if (Math.abs(value) >= 10_000) return `${(value / 1_000).toFixed(1)}k`;
  if (Number.isInteger(value) && digits === 0) return value.toLocaleString("zh-CN");
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
  };
  return map[purpose] ?? purpose;
}
