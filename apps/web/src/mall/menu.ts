import { MALL_ADMIN } from "./admin-registry.ts";

export function mallMenuAllowed(path: string, permissions: readonly string[]): boolean {
  if (path === "/admin/infra") return permissions.length > 0;
  const normalized = path.replace(/^\/admin\/(service|commerce|system)\//, "/admin/");
  const entry = MALL_ADMIN.find((item) => normalized === `/admin/mall/${item.module}`);
  return entry ? mallModuleAllowed(entry.module, permissions) : true;
}

export function mallModuleAllowed(module: string, permissions: readonly string[]) {
  const entry = MALL_ADMIN.find((item) => item.module === module);
  return Boolean(entry && [entry.permission, ...entry.additionalPermissions ?? []]
    .some((permission) => permissions.includes(permission)));
}
