import { Tooltip } from "antd";

type ConfidenceBadgeProps = {
  confidence?: number | null;
  route?: string | null;
  refused?: boolean;
};

const ROUTE_LABELS: Record<string, string> = {
  rag: "知识库",
  tool: "业务查询",
  ticket: "工单",
  handoff: "转人工",
  clarify: "澄清",
  refuse: "拒答",
};

function tone(confidence: number | null | undefined, refused: boolean) {
  if (refused) return "danger";
  if (confidence == null) return "neutral";
  if (confidence >= 0.75) return "ok";
  if (confidence >= 0.45) return "warn";
  return "danger";
}

/** Compact chips for answer route and grounding confidence. */
export function ConfidenceBadge({
  confidence,
  route,
  refused = false,
}: ConfidenceBadgeProps) {
  if (confidence == null && !route && !refused) return null;
  const routeLabel = route ? (ROUTE_LABELS[route] ?? route) : null;
  // Confidence is only meaningful for grounded answers.
  const showConfidence =
    confidence != null && !refused && (route == null || route === "rag");
  const t = tone(confidence, refused);

  return (
    <span className="af-chip-row">
      {routeLabel ? <span className="af-chip">{routeLabel}</span> : null}
      {refused ? (
        <span className="af-confidence af-confidence--danger">
          证据不足 · 已拒答
        </span>
      ) : null}
      {showConfidence ? (
        <Tooltip title="回答与检索证据的匹配程度">
          <span className={`af-confidence af-confidence--${t}`}>
            置信度 {Math.round((confidence as number) * 100)}%
          </span>
        </Tooltip>
      ) : null}
    </span>
  );
}
