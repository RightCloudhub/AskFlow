import { useQuery } from "@tanstack/react-query";
import { getToken } from "../api/client";
import { authService } from "../services/auth-service";
import { AuthKeys } from "./query-keys";

export function useMe(enabled = true) {
  return useQuery({
    queryKey: AuthKeys.me(),
    queryFn: () => authService.me(),
    enabled: enabled && Boolean(getToken()),
    retry: false,
    staleTime: 60_000,
  });
}
