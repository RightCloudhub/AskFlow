export type Order = {
  id: string;
  status: string;
  total_cents: number;
  currency: string;
  version: number;
  refunded_cents: number;
  refund_reserved_cents?: number;
  created_at?: string;
  tracking_number?: string;
  items?: { id: string; title_snapshot: string; price_cents: number; qty: number; total_cents: number }[];
};

export type OrderFlowProps = { order: Order; reload: () => Promise<void>; onExit: () => void };
export const REFUNDABLE_STATUSES = new Set(["PAID", "SHIPPED", "DELIVERED", "COMPLETED", "PARTIALLY_REFUNDED"]);

export function refundableAmount(order: Order) {
  return Math.max(0, order.total_cents - order.refunded_cents - (order.refund_reserved_cents ?? 0));
}

export function orderRevision(order: Order) {
  return JSON.stringify([order.id, order.version, order.status, order.total_cents, order.refunded_cents, order.refund_reserved_cents]);
}
