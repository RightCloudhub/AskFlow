import { useCallback } from "react";
import { mall } from "./client";
import { useLoad, type Page, type Row } from "./shared";

export function useRoleChoices(active: boolean) {
  const query = useLoad(useCallback(() => active ? mall<Page<Row>>("/api/v1/admin/mall/roles")
    : Promise.resolve({ items: [] }), [active]));
  return { ...query, options: (query.data?.items ?? []).map((row) => ({ value: String(row.code), label: String(row.name) })) };
}
