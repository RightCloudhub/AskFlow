import { useMe } from "../hooks/use-auth";
import { getToken } from "../api/client";
import { useFeatures } from "../plugins/features";
import { ADMIN_NAV } from "../plugins/registry";
import { useMallPermissions } from "../mall/permissions";
import { accessibleNavigation, ADMIN_WORKSPACES } from "./access-policy";

export function useAdminAccess() {
  const features = useFeatures();
  const me = useMe();
  const grants = useMallPermissions();
  const authenticated = Boolean(getToken());
  const loading = !features.ready || (authenticated && (me.isPending || grants.loading));
  const error = authenticated && (me.isError || Boolean(grants.error));
  const identity = { role: me.data?.role, permissions: grants.permissions };
  const items = loading || error || !authenticated ? [] : accessibleNavigation({
    items: ADMIN_NAV, features: features.features, identity,
  });
  const workspaces = ADMIN_WORKSPACES.filter((workspace) => items.some((item) =>
    item.to.startsWith(`/admin/${workspace.id}/`)));
  async function reload() { await Promise.all([me.refetch(), grants.reload()]); }
  return { identity, items, workspaces, loading, error, reload, user: me.data };
}
