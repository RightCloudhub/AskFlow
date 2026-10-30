import { readableError } from "../components/common/error-text.ts";

const SERVER_ERROR_STATUS = 500;

export class MallRequestError extends Error {
  readonly code: string;
  readonly status: number;

  constructor(data: unknown, status: number) {
    super(readableError(data));
    this.name = "MallRequestError";
    this.status = status;
    const payload = data && typeof data === "object" ? data as Record<string, unknown> : {};
    this.code = typeof payload.code === "string" ? payload.code : "";
  }
}

export function hasMallError(error: unknown, code: string) {
  return error instanceof MallRequestError && error.code === code;
}

export function isUncertainMallError(error: unknown) {
  if (!(error instanceof MallRequestError)) return true;
  return error.status >= SERVER_ERROR_STATUS || error.code === "idempotency_in_progress";
}
