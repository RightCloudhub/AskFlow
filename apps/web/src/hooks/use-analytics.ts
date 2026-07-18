import { useQuery } from "@tanstack/react-query";
import { analyticsService } from "../services/analytics-service";
import { AnalyticsKeys } from "./query-keys";

export function useAnalyticsSummary() {
  return useQuery({
    queryKey: AnalyticsKeys.summary(),
    queryFn: () => analyticsService.summary(),
    staleTime: 30_000,
  });
}
