import { Tooltip } from "antd";

type ConfidenceBadgeProps = { confidence?: number | null; route?: string | null; refused?: boolean };
const PERCENT_SCALE = 100;
const ROUTE_LABELS: Record<string, string> = {
  rag: "知识库回答", tool: "业务查询", ticket: "工单服务", handoff: "人工服务", clarify: "补充信息", refuse: "证据不足",
};

function confidenceLabel({ confidence, route, refused }: ConfidenceBadgeProps) {
  if (confidence == null || !Number.isFinite(confidence) || refused || (route != null && route !== "rag")) return null;
  const percent = Math.round(Math.min(1, Math.max(0, confidence)) * PERCENT_SCALE);
  return `置信度 ${percent}%`;
}

/** Routes and confidence explain the answer without competing with it. */
export function ConfidenceBadge(props: ConfidenceBadgeProps) {
  const { route, refused } = props;
  const label = confidenceLabel(props);
  if (!label && !route && !refused) return null;
  return <span className="af-answer-meta">
    {route && <span>{ROUTE_LABELS[route] ?? route}</span>}
    {refused && <span>证据不足，未作答</span>}
    {label && <Tooltip title="回答与检索证据的匹配程度，并非正确率保证">
      <span>{label}</span>
    </Tooltip>}
  </span>;
}
