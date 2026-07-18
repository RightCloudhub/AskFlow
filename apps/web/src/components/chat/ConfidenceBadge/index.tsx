type ConfidenceBadgeProps = {
  confidence?: number | null;
  route?: string | null;
  refused?: boolean;
};

function tone(confidence: number | null | undefined, refused: boolean) {
  if (refused) return "danger";
  if (confidence == null) return "neutral";
  if (confidence >= 0.75) return "ok";
  if (confidence >= 0.45) return "warn";
  return "danger";
}

export function ConfidenceBadge({
  confidence,
  route,
  refused = false,
}: ConfidenceBadgeProps) {
  if (confidence == null && !route && !refused) return null;
  const t = tone(confidence, refused);
  const parts: string[] = [];
  if (confidence != null) parts.push(`置信度 ${confidence.toFixed(2)}`);
  if (route) parts.push(route);
  if (refused) parts.push("拒答");

  return (
    <span className={`af-confidence af-confidence--${t}`}>{parts.join(" · ")}</span>
  );
}
