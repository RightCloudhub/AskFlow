import { useEffect, useState } from "react";
import { AUTH_EVENT, getToken } from "../api/client";
import { CORE_FEATURES } from "./registry";

type Discovery = { profile?: string; features: string[] };

async function discover(): Promise<Discovery> {
  const token = getToken();
  if (token) {
    const response = await fetch("/api/v1/admin/features", { headers: { Authorization: `Bearer ${token}` } });
    if (response.ok) return response.json() as Promise<Discovery>;
  }
  const response = await fetch("/api/v1/mall/features");
  if (response.ok) {
    const data: Discovery = await response.json();
    return { profile: data.profile ?? "mall", features: [...CORE_FEATURES, ...data.features] };
  }
  return { profile: "unknown", features: [...CORE_FEATURES] };
}

export function useFeatureDiscovery(envSet: Set<string> | null) {
  const [profile, setProfile] = useState(envSet ? "env" : "unknown");
  const [features, setFeatures] = useState(envSet ?? new Set<string>(CORE_FEATURES));
  const [ready, setReady] = useState(Boolean(envSet));
  const [authKey, setAuthKey] = useState(getToken() ?? "");
  useEffect(() => {
    const changed = () => setAuthKey(getToken() ?? "");
    window.addEventListener(AUTH_EVENT, changed);
    return () => window.removeEventListener(AUTH_EVENT, changed);
  }, []);
  useEffect(() => {
    if (envSet) return;
    let cancelled = false;
    setReady(false);
    void discover().catch(() => ({ profile: "unknown", features: [...CORE_FEATURES] })).then((data) => {
      if (cancelled) return;
      setProfile(data.profile ?? "unknown");
      setFeatures(new Set(data.features.length ? data.features : CORE_FEATURES));
      setReady(true);
    });
    return () => { cancelled = true; };
  }, [authKey, envSet]);
  return { ready, profile, features };
}
