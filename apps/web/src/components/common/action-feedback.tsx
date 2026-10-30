import { useRef, useState } from "react";
import { Alert } from "antd";
import { readableError } from "./error-text";

export { readableError } from "./error-text";

type Notice = { kind: "success" | "error"; message: string };

export function useActionFeedback() {
  const [notice, setNotice] = useState<Notice>();
  const [busy, setBusy] = useState(false);
  const locked = useRef(false);
  async function run(action: () => Promise<unknown>, success?: string) {
    if (locked.current) return false;
    locked.current = true;
    setBusy(true);
    setNotice(undefined);
    try {
      await action();
      if (success) setNotice({ kind: "success", message: success });
      return true;
    } catch (error) {
      setNotice({ kind: "error", message: readableError(error) });
      return false;
    } finally {
      locked.current = false;
      setBusy(false);
    }
  }
  return { notice, busy, run, clear: () => setNotice(undefined),
    succeed: (message: string) => setNotice({ kind: "success", message }) };
}

export function ActionFeedback({ state }: { state: ReturnType<typeof useActionFeedback> }) {
  if (!state.notice) return null;
  return <div className="af-action-notice" aria-live="polite">
    <Alert type={state.notice.kind} title={state.notice.message} showIcon closable onClose={state.clear} />
  </div>;
}
