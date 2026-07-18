// Dependency-free helpers for the JSON tree viewer (components/common/json/*).
// Classification/formatting live here so each renderer component stays small
// and the whole viewer ships with zero third-party dependencies.

export type ValueKind =
  | "string"
  | "number"
  | "boolean"
  | "null"
  | "undefined"
  | "object"
  | "array";

export type JsonEntry = { key: string; value: unknown };

const PRIMITIVE_TYPEOF = new Set(["string", "number", "boolean"]);

/** Braces per container kind: [open, close]. */
export const BRACES: Record<"object" | "array", [string, string]> = {
  object: ["{", "}"],
  array: ["[", "]"],
};

export function kindOf(value: unknown): ValueKind {
  if (value === null) return "null";
  if (value === undefined) return "undefined";
  if (Array.isArray(value)) return "array";
  const t = typeof value;
  if (t === "object") return "object";
  if (PRIMITIVE_TYPEOF.has(t)) return t as ValueKind;
  return "string";
}

export function isContainer(kind: ValueKind): boolean {
  return kind === "object" || kind === "array";
}

/** Normalised child entries; index labels for arrays, keys for objects. */
export function entriesOf(value: unknown, kind: ValueKind): JsonEntry[] {
  if (kind === "array") {
    return (value as unknown[]).map((v, i) => ({ key: String(i), value: v }));
  }
  if (kind === "object") {
    return Object.entries(value as Record<string, unknown>).map(([key, v]) => ({ key, value: v }));
  }
  return [];
}

/** Collapsed-container badge, e.g. "{ 5 字段 }" / "[ 3 项 ]". */
export function summaryLabel(kind: ValueKind, count: number): string {
  const isArray = kind === "array";
  const [open, close] = isArray ? BRACES.array : BRACES.object;
  const noun = isArray ? "项" : "字段";
  return `${open} ${count} ${noun} ${close}`;
}

/** Render a leaf value as source text: strings keep quotes/escapes. */
export function formatPrimitive(value: unknown, kind: ValueKind): string {
  if (kind === "string") return JSON.stringify(value);
  if (kind === "null") return "null";
  if (kind === "undefined") return "undefined";
  return String(value);
}

export function toPrettyJson(value: unknown): string {
  try {
    const text = JSON.stringify(value, null, 2);
    return text ?? String(value);
  } catch {
    return String(value);
  }
}

/** Clipboard write; resolves false when unavailable (insecure context / denied). */
export async function copyToClipboard(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    return false;
  }
}
