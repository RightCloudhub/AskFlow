import { useRef, useState } from "react";
import { useActionFeedback } from "../components/common/action-feedback";
import { mall, write } from "./client";
import { hasMallError } from "./request-error";
import { orderRevision, type OrderFlowProps } from "./order-types";

export type OrderPayment = {
  id: string; status: string; currency: string; amount_cents: number; wallet_cents: number; external_cents: number;
};
type Stage = "amount" | "identity" | "review" | "result";
type PaymentProps = OrderFlowProps & { walletEnabled: boolean };
const STAGES: Stage[] = ["amount", "review", "result"];
const VERIFIED_STAGES: Stage[] = ["amount", "identity", "review", "result"];
const TITLES: Record<Stage, string> = { amount: "支付方式", identity: "确认身份", review: "核对支付", result: "支付结果" };

function usePaymentState({ order, walletEnabled }: PaymentProps) {
  const [stage, setStage] = useState<Stage>("amount");
  const [walletValue, setWallet] = useState(0);
  const [payment, setPayment] = useState<OrderPayment>();
  const [token, setToken] = useState("");
  const [identityRequired, requireIdentity] = useState(false);
  const [identityRevision, setIdentityRevision] = useState(0);
  const [identityBusy, setIdentityBusy] = useState(false);
  const [reviewRevision, setReviewRevision] = useState("");
  const [settlementSent, setSettlementSent] = useState(false);
  const request = useRef({ signature: "", key: crypto.randomUUID() });
  const settlementKey = useRef(crypto.randomUUID());
  const feedback = useActionFeedback();
  const stages = identityRequired ? VERIFIED_STAGES : STAGES;
  const wallet = walletEnabled ? walletValue : 0;
  const reviewValid = reviewRevision === orderRevision(order);
  const payable = order.status === "PENDING_PAYMENT";
  const validAmount = Number.isSafeInteger(wallet) && wallet >= 0 && wallet <= order.total_cents;
  const busy = identityBusy || feedback.busy;
  function back(index: number) {
    if (busy || payment || index < 0 || index >= stages.indexOf(stage)) return;
    setStage(stages[index]); feedback.clear();
  }
  function verifyAgain() {
    setToken(""); requireIdentity(true); setIdentityRevision((value) => value + 1); setStage("identity");
  }
  return { stage, setStage, wallet, setWallet, payment, setPayment, token, setToken, identityRequired,
    identityRevision, identityBusy, setIdentityBusy, reviewValid, setReviewRevision, settlementSent, setSettlementSent,
    request, settlementKey, feedback, busy, payable, validAmount, back, verifyAgain,
    current: stages.indexOf(stage), titles: stages.map((item) => TITLES[item]) };
}

type PaymentState = ReturnType<typeof usePaymentState>;

function usePaymentRequests(state: PaymentState, { order, reload }: PaymentProps) {
  async function start() {
    if (state.payment || !state.payable || !state.validAmount || !state.reviewValid) return;
    await state.feedback.run(async () => {
      const body = { order_id: order.id, method: state.wallet ? "mixed" : "mock",
        wallet_cents: state.wallet, step_up_token: state.token };
      const signature = JSON.stringify(body);
      if (state.request.current.signature !== signature) state.request.current = { signature, key: crypto.randomUUID() };
      try {
        const payment = await write<OrderPayment>("/payment", body, { key: state.request.current.key });
        state.setPayment(payment);
        state.setStage("result");
      } catch (error) {
        if (hasMallError(error, "step_up_required")) {
          state.verifyAgain();
          throw new Error("本次支付需要验证身份，请完成验证后继续。");
        }
        throw error;
      }
      await reload();
    });
  }
  async function readResult() {
    if (!state.payment) return;
    const payment = await mall<OrderPayment>(`/payment/${encodeURIComponent(state.payment.id)}`);
    state.setPayment(payment);
    await reload();
  }
  async function settle() {
    const payment = state.payment;
    if (!payment || payment.status !== "pending" || state.settlementSent) return;
    await state.feedback.run(async () => {
      await write(`/payment/${encodeURIComponent(payment.id)}/mock`, { status: "succeeded" }, { key: state.settlementKey.current });
      state.setSettlementSent(true);
      await readResult();
    });
  }
  return { start, settle, refresh: () => state.feedback.run(readResult) };
}

export function useOrderPaymentFlow(props: PaymentProps) {
  const state = usePaymentState(props);
  const requests = usePaymentRequests(state, props);
  function next() {
    if (state.busy || state.payment || !state.payable) return;
    state.feedback.clear();
    if (!state.validAmount) return;
    if (state.identityRequired && (state.stage === "amount" || !state.token)) { state.setStage("identity"); return; }
    state.setReviewRevision(orderRevision(props.order));
    state.setStage("review");
  }
  return { ...state, ...requests, next };
}
