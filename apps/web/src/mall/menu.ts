import { MALL_ADMIN } from "./admin-registry.ts";

export function mallMenuAllowed(path: string, permissions: readonly string[]): boolean {
  if (path === "/admin/infra") return permissions.length > 0;
  const entry = MALL_ADMIN.find((item) => path === `/admin/mall/${item.module}`);
  return entry ? permissions.includes(entry.permission) : true;
}
