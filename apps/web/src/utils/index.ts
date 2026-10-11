/** Shared pure helpers (prefer colocating near feature when small). */

/** Parse an API timestamp; naive ISO strings from the API are UTC. */
export function parseApiDate(iso?: string | null): Date | null {
  if (!iso) return null;
  const hasZone = /([zZ]|[+-]\d{2}:?\d{2})$/.test(iso);
  const d = new Date(hasZone ? iso : `${iso}Z`);
  return Number.isNaN(d.getTime()) ? null : d;
}

/** Local "YYYY-MM-DD HH:mm" (or with seconds) for tables and details. */
export function formatDateTime(
  iso?: string | null,
  withSeconds = false,
): string {
  const d = parseApiDate(iso);
  if (!d) return "—";
  const pad = (n: number) => String(n).padStart(2, "0");
  const base = `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
  return withSeconds ? `${base}:${pad(d.getSeconds())}` : base;
}
