import { useEffect, useState, type ReactNode } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { getSessionVersion, SESSION_EVENT, synchronizeSession, TOKEN_KEY } from "../api/client";
import { disposeChatSocket } from "../services/chat-ws";

/** Remount local state and discard cached customer data when accounts change. */
export function SessionBoundary({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [version, setVersion] = useState(getSessionVersion);
  useEffect(() => {
    const changed = () => {
      queryClient.clear();
      disposeChatSocket();
      setVersion(getSessionVersion());
    };
    const stored = (event: StorageEvent) => {
      if (event.key === TOKEN_KEY || event.key === null) synchronizeSession();
    };
    window.addEventListener(SESSION_EVENT, changed);
    window.addEventListener("storage", stored);
    return () => {
      window.removeEventListener(SESSION_EVENT, changed);
      window.removeEventListener("storage", stored);
    };
  }, [queryClient]);
  return <SessionContents key={version}>{children}</SessionContents>;
}

function SessionContents({ children }: { children: ReactNode }) { return <>{children}</>; }
