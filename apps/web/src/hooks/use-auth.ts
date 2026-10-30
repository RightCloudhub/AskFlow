import { useQuery } from "@tanstack/react-query";
import { getSessionVersion, getToken } from "../api/client";
import { authService } from "../services/auth-service";
import { AuthKeys } from "./query-keys";

const IDENTITY_REFRESH_MS = 30_000;

export function useMe(enabled = true) {
  return useQuery({
    queryKey: [...AuthKeys.me(), getSessionVersion()],
    queryFn: () => authService.me(),
    enabled: enabled && Boolean(getToken()),
    retry: false,
    refetchOnWindowFocus: true,
    staleTime: IDENTITY_REFRESH_MS,
    refetchInterval: IDENTITY_REFRESH_MS,
  });
}
