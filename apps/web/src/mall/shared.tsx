import { useCallback, useEffect, useRef, useState } from "react";
import { Alert, Button, Skeleton } from "antd";
import { readableError } from "../components/common/action-feedback";

export { ActionForm } from "./action-form";
export type { Field } from "./form-fields";

export type Row = Record<string, unknown>;
export type Page<T> = { items: T[]; next_cursor?: string | null };
const LOADING_ROWS = 3;

export function useLoad<T>(loader: () => Promise<T>) {
  const generation = useRef(0);
  const [data, setData] = useState<T>();
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [updatedAt, setUpdatedAt] = useState<Date>();
  const reload = useCallback(async () => {
    const request = ++generation.current;
    setLoading(true);
    try {
      const result = await loader();
      if (request === generation.current) { setData(result); setError(""); setUpdatedAt(new Date()); }
    } catch (reason) {
      if (request === generation.current) setError(readableError(reason));
    } finally { if (request === generation.current) setLoading(false); }
  }, [loader]);
  useEffect(() => {
    setData(undefined);
    setError("");
    setUpdatedAt(undefined);
    void reload();
    return () => { generation.current += 1; };
  }, [reload]);
  return { data, error, loading, reload, updatedAt };
}

export function Feedback({ error, loading, reload, updatedAt }: {
  error?: string; loading?: boolean; reload?: () => Promise<void>; updatedAt?: Date;
}) {
  return <div className="af-mall-feedback" aria-live="polite">
    {error && <Alert type="error" title="暂时无法完成请求" description={readableError(error)} showIcon
      action={reload && <Button loading={loading} onClick={() => void reload()}>重试</Button>} />}
    {loading && !updatedAt && <div className="af-mall-loading" role="status" aria-label="正在读取数据">
      <Skeleton active={false} title={false} paragraph={{ rows: LOADING_ROWS }} />
    </div>}
    {loading && updatedAt && <p className="af-mall-note">正在更新，保留上次读取的内容。</p>}
  </div>;
}
