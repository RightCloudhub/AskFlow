import { useQuery } from "@tanstack/react-query";
import { getSessionVersion, getToken } from "../api/client";
import { useFeatures } from "../plugins/features";
import { mall } from "./client";

const PERMISSIONS_STALE_MS = 30_000;

export function useMallPermissions() {
  const { enabled } = useFeatures();
  const active = enabled("mall_admin") && Boolean(getToken());
  const query = useQuery({
    queryKey: ["admin-permissions", getSessionVersion()],
    queryFn: () => mall<{ permissions: string[] }>("/admin/permissions"),
    enabled: active,
    staleTime: PERMISSIONS_STALE_MS,
    refetchInterval: PERMISSIONS_STALE_MS,
    refetchOnWindowFocus: true,
    retry: false,
  });
  async function reload() { if (active) await query.refetch(); }
  return { permissions: active && !query.isError ? query.data?.permissions ?? [] : [],
    error: active && query.isError ? "无法读取账号权限，请重试。" : "",
    loading: active && query.isPending, reload };
}
