import { useEffect, useState, type Dispatch, type SetStateAction, type MutableRefObject } from "react";
import { MESSAGE_SYNC_INTERVAL_MS } from "../../services/message-sync";
import { widgetFetch, type WidgetMessage, type WidgetSession } from "./widget-service";

type Options = {
  session?: WidgetSession;
  paused: boolean;
  setMessages: Dispatch<SetStateAction<WidgetMessage[]>>;
  locked: MutableRefObject<boolean>;
  generation: MutableRefObject<number>;
};

function mergeHistory(previous: WidgetMessage[], rows: WidgetMessage[]) {
  const failed = previous.filter((row) => row.failed && !rows.some((saved) => saved.id === row.id));
  const next = [...rows, ...failed];
  return JSON.stringify(previous) === JSON.stringify(next) ? previous : next;
}

/** Cancel old reads on send/reconnect so a stale response cannot replace a draft or new reply. */
export function useWidgetSync({ session, paused, setMessages, locked, generation }: Options) {
  const [syncError, setSyncError] = useState("");
  useEffect(() => {
    if (!session || paused) return;
    const controller = new AbortController();
    const request = generation.current;
    let timer: number;
    let reading = false;
    const current = () => !controller.signal.aborted && !locked.current && generation.current === request;
    async function refresh() {
      if (reading || controller.signal.aborted) return;
      window.clearTimeout(timer);
      reading = true;
      try {
        const rows = await widgetFetch<WidgetMessage[]>(`/widget/conversations/${session!.conversation_id}/messages`, {
          token: session!.access_token, signal: controller.signal,
        });
        if (!current()) return;
        setMessages((previous) => mergeHistory(previous, rows));
        setSyncError("");
      } catch {
        if (current()) setSyncError("新消息暂时无法同步，正在自动重试。");
      } finally {
        reading = false;
        if (!controller.signal.aborted) timer = window.setTimeout(tick, MESSAGE_SYNC_INTERVAL_MS);
      }
    }
    function tick() {
      if (!document.hidden) void refresh();
      else timer = window.setTimeout(tick, MESSAGE_SYNC_INTERVAL_MS);
    }
    function resume() { if (!document.hidden) void refresh(); }
    void refresh();
    document.addEventListener("visibilitychange", resume);
    window.addEventListener("online", resume);
    return () => {
      controller.abort();
      window.clearTimeout(timer);
      document.removeEventListener("visibilitychange", resume);
      window.removeEventListener("online", resume);
    };
  }, [session, paused, setMessages, locked, generation]);
  return syncError;
}
