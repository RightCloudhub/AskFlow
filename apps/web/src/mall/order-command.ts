import { useRef, useState } from "react";
import { useActionFeedback } from "../components/common/action-feedback";
import { write } from "./client";
import { hasMallError, isUncertainMallError } from "./request-error";
import { orderRevision, type OrderFlowProps } from "./order-types";
import type { Row } from "./shared";

type Confirmation = { confirmation_token: string; expires_at: string; requires_human_approval: boolean };
type Attempt = { key: string; body: Row; revision: string; signature: string };
type Pending = Attempt & Confirmation;
type CommandProps = OrderFlowProps & { kind: "cancel" | "refunds" };

function confirmationFrom(response: Row): Confirmation {
  if (typeof response.confirmation_token !== "string" || !response.confirmation_token) {
    throw new Error("未取得确认信息，请重新核对后再试。");
  }
  return { confirmation_token: response.confirmation_token, expires_at: String(response.expires_at ?? ""),
    requires_human_approval: response.requires_human_approval === true };
}

function useCommandState(order: OrderFlowProps["order"]) {
  const [pending, setPending] = useState<Pending>();
  const [complete, setComplete] = useState(false);
  const [awaitingResult, setAwaitingResult] = useState(false);
  const attempt = useRef<Attempt>();
  const revision = orderRevision(order);
  const latestRevision = useRef(revision);
  latestRevision.current = revision;
  const feedback = useActionFeedback();
  function invalidate() {
    setPending(undefined);
    attempt.current = undefined;
    feedback.clear();
  }
  const currentPending = pending?.revision === revision || awaitingResult ? pending : undefined;
  return { pending: currentPending, complete, awaitingResult, setAwaitingResult, attempt,
    revision, latestRevision, feedback, setPending, setComplete, invalidate };
}

export function useOrderCommand({ order, kind, reload }: CommandProps) {
  const state = useCommandState(order);
  const path = `/order/orders/${encodeURIComponent(order.id)}/${kind}`;
  async function prepare(readBody: () => Row) {
    if (state.complete || state.awaitingResult) return false;
    return state.feedback.run(async () => {
      const body = readBody();
      const signature = JSON.stringify([state.revision, body]);
      if (state.attempt.current?.signature !== signature) {
        state.attempt.current = { key: crypto.randomUUID(), body, revision: state.revision, signature };
      }
      const attempt = state.attempt.current;
      const response = await write<Row>(path, { ...attempt.body, confirmation_token: "" }, { key: attempt.key });
      if (attempt.revision !== state.latestRevision.current) throw new Error("订单已更新，请重新核对。");
      state.setPending({ ...attempt, ...confirmationFrom(response) });
    });
  }
  async function submit() {
    if (!state.pending || state.complete) return false;
    return state.feedback.run(async () => {
      const pending = state.pending;
      if (!pending) return;
      if (!state.awaitingResult && pending.revision !== state.latestRevision.current) throw new Error("订单已更新，请重新核对。");
      state.setAwaitingResult(true);
      try {
        await write(path, { ...pending.body, confirmation_token: pending.confirmation_token }, { key: pending.key });
      } catch (error) {
        state.setAwaitingResult(isUncertainMallError(error));
        if (hasMallError(error, "confirmation_invalid")) state.invalidate();
        throw error;
      }
      state.setComplete(true);
      state.setAwaitingResult(false);
      state.setPending(undefined);
      await reload();
    });
  }
  return { ...state, prepare, submit, busy: state.feedback.busy, locked: state.feedback.busy || state.awaitingResult };
}
