export const MINOR_UNITS = 100;
export const MONEY_DECIMALS = 2;

export function majorToMinor(amount: number) {
  const cents = Math.round(amount * MINOR_UNITS);
  if (!Number.isFinite(amount) || !Number.isSafeInteger(cents)) throw new Error("金额无效，请填写有效金额。");
  return cents;
}

export function currencySymbol(currency = "CNY") {
  return new Intl.NumberFormat("zh-CN", { style: "currency", currency }).formatToParts(0)
    .find((part) => part.type === "currency")?.value;
}

export function submissionValues(values: Record<string, unknown>, fields: Array<{ name: string; kind?: string }>) {
  const result = { ...values };
  for (const field of fields) {
    if (field.kind === "money" && typeof result[field.name] === "number") result[field.name] = majorToMinor(Number(result[field.name]));
  }
  return result;
}
