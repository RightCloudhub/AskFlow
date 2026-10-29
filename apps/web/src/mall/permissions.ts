import { useCallback } from "react";
import { useFeatures } from "../plugins/features";
import { mall } from "./client";
import { useLoad } from "./shared";

export function useMallPermissions() {
  const { enabled } = useFeatures();
  const active = enabled("mall_admin");
  const load = useCallback(() => active ? mall<{ permissions: string[] }>("/admin/permissions") :
    Promise.resolve({ permissions: [] as string[] }), [active]);
  const query = useLoad(load);
  return { ...query, permissions: query.data?.permissions ?? [] };
}
