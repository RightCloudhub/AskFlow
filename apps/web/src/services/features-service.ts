import { api } from "../api/client";
import type { FeaturesResponse } from "../plugins/types";

export const featuresService = {
  get: () => api<FeaturesResponse>("/api/v1/admin/features"),
};
