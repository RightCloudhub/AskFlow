import { createContext, useContext, useEffect, useMemo, type ReactNode } from "react";
import { setUnauthorizedRecovery } from "../api/client";
import { refreshMallSession } from "../mall/session";
import { CORE_FEATURES, parseEnvFeatures } from "./registry";
import { useFeatureDiscovery } from "./discovery";

type FeaturesState = {
  ready: boolean;
  profile: string;
  features: Set<string>;
  enabled: (id: string) => boolean;
};

const FAIL_CLOSED = new Set<string>(CORE_FEATURES);
const FeaturesContext = createContext<FeaturesState>({
  ready: false, profile: "unknown", features: FAIL_CLOSED,
  enabled: (id) => FAIL_CLOSED.has(id),
});

export function FeaturesProvider({ children }: { children: ReactNode }) {
  const envSet = useMemo(parseEnvFeatures, []);
  const { ready, profile, features } = useFeatureDiscovery(envSet);
  const mallAccount = features.has("mall_account");
  useEffect(() => {
    setUnauthorizedRecovery(mallAccount ? refreshMallSession : null);
    return () => setUnauthorizedRecovery(null);
  }, [mallAccount]);
  const value = useMemo<FeaturesState>(() => ({ ready, profile, features,
    enabled: (id) => features.has(id),
  }), [ready, profile, features]);
  return <FeaturesContext.Provider value={value}>{children}</FeaturesContext.Provider>;
}

export function useFeatures(): FeaturesState {
  return useContext(FeaturesContext);
}
