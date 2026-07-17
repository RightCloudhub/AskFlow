import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { api } from "../api/client";
import { CORE_FEATURES, parseEnvFeatures } from "./registry";
import type { FeaturesResponse } from "./types";

type FeaturesState = {
  ready: boolean;
  profile: string;
  features: Set<string>;
  enabled: (id: string) => boolean;
};

/** Fail closed: only core until discovery succeeds (or env overrides). */
const FAIL_CLOSED = new Set<string>(CORE_FEATURES);

const FeaturesContext = createContext<FeaturesState>({
  ready: false,
  profile: "unknown",
  features: FAIL_CLOSED,
  enabled: (id: string) => FAIL_CLOSED.has(id),
});

export function FeaturesProvider({ children }: { children: ReactNode }) {
  const envSet = parseEnvFeatures();
  const [profile, setProfile] = useState(envSet ? "env" : "unknown");
  const [features, setFeatures] = useState<Set<string>>(
    () => envSet ?? new Set(FAIL_CLOSED)
  );
  const [ready, setReady] = useState(Boolean(envSet));

  useEffect(() => {
    if (envSet) return;
    let cancelled = false;
    (async () => {
      try {
        const data = await api<FeaturesResponse>("/api/v1/admin/features");
        if (cancelled) return;
        setProfile(data.profile || "unknown");
        // Empty list → fail closed to core, not full catalog
        const ids =
          data.features?.length > 0 ? data.features : [...CORE_FEATURES];
        setFeatures(new Set(ids));
      } catch {
        if (!cancelled) {
          setProfile("unknown");
          setFeatures(new Set(CORE_FEATURES));
        }
      } finally {
        if (!cancelled) setReady(true);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [envSet]);

  const value = useMemo<FeaturesState>(
    () => ({
      ready,
      profile,
      features,
      enabled: (id: string) => features.has(id),
    }),
    [ready, profile, features]
  );

  return (
    <FeaturesContext.Provider value={value}>{children}</FeaturesContext.Provider>
  );
}

export function useFeatures(): FeaturesState {
  return useContext(FeaturesContext);
}
