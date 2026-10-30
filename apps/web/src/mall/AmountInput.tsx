import { InputNumber } from "antd";
import { currencySymbol, majorToMinor, MINOR_UNITS, MONEY_DECIMALS } from "./money-values";

type AmountProps = { value: number; onChange: (cents: number) => void; max?: number;
  min?: number; currency: string; disabled?: boolean; label: string; describedBy?: string };

export function AmountInput({ value, onChange, max, min = 0, currency, disabled, label, describedBy }: AmountProps) {
  return <InputNumber value={value / MINOR_UNITS} min={min / MINOR_UNITS}
    max={max == null ? undefined : max / MINOR_UNITS} precision={MONEY_DECIMALS} prefix={currencySymbol(currency)}
    disabled={disabled} aria-label={label} aria-describedby={describedBy}
    onChange={(amount) => onChange(amount == null ? min : majorToMinor(amount))} />;
}
