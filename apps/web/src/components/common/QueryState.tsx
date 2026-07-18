import { Alert, Empty, Spin } from "antd";
import type { ReactNode } from "react";

type QueryStateProps = {
  isLoading?: boolean;
  isError?: boolean;
  error?: unknown;
  isEmpty?: boolean;
  emptyDescription?: string;
  children: ReactNode;
};

function errorMessage(error: unknown): string {
  if (error instanceof Error) return error.message;
  return String(error ?? "加载失败");
}

/** Shared loading / error / empty wrapper for query-driven pages. */
export function QueryState({
  isLoading,
  isError,
  error,
  isEmpty,
  emptyDescription = "暂无数据",
  children,
}: QueryStateProps) {
  if (isLoading) {
    return (
      <div className="af-query-state">
        <Spin tip="加载中…" />
      </div>
    );
  }
  if (isError) {
    return (
      <Alert
        type="error"
        showIcon
        message="加载失败"
        description={errorMessage(error)}
        style={{ marginBottom: 16 }}
      />
    );
  }
  if (isEmpty) {
    return (
      <div className="af-query-state">
        <Empty description={emptyDescription} />
      </div>
    );
  }
  return <>{children}</>;
}
