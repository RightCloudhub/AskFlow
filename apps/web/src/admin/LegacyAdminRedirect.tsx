import { Navigate, useLocation } from "react-router-dom";
import { workspacePath } from "./access-policy";

export function LegacyAdminRedirect({ path }: { path: string }) {
  const location = useLocation();
  return <Navigate to={{ pathname: workspacePath(path), search: location.search, hash: location.hash }} replace />;
}
