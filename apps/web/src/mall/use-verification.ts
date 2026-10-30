import { useEffect, useRef, useState } from "react";
import { write } from "./client";
import { useActionFeedback } from "../components/common/action-feedback";

export type Proof = { verification_id: string; verification_token: string };
export type VerificationOptions = {
  purpose: string;
  channel?: "email" | "sms";
  onProof?: (proof?: Proof, recipient?: string) => void;
};

export function normalizeContact(value: string) {
  const target = value.trim();
  return target.startsWith("+") ? target.replace(/[\s()-]/g, "") : target;
}

function contactPayload(target: string, options: VerificationOptions) {
  const channel = options.channel ?? (target.startsWith("+") ? "sms" : "email");
  if (channel === "sms" && !target.startsWith("+")) throw new Error("请填写包含国家区号的手机号。");
  if (channel === "email" && !target.includes("@")) throw new Error("请填写有效的邮箱地址。");
  return { target, channel, purpose: options.purpose };
}

function useVerificationState(onProof: VerificationOptions["onProof"]) {
  const [current, setCurrent] = useState(0);
  const [challenge, setChallenge] = useState("");
  const [recipient, setRecipient] = useState("");
  const [proof, setProof] = useState<Proof>();
  const generation = useRef(0);
  const feedback = useActionFeedback();
  useEffect(() => () => { generation.current += 1; }, []);
  function invalidate() {
    generation.current += 1;
    setChallenge(""); setProof(undefined); onProof?.(undefined); feedback.clear();
  }
  function accept(next: Proof) {
    setProof(next); onProof?.(next, recipient); setCurrent(2);
  }
  function back(index: number) {
    if (feedback.busy || index < 0 || index >= current) return;
    setCurrent(index); feedback.clear();
  }
  return { current, setCurrent, challenge, setChallenge, recipient, setRecipient,
    proof, generation, feedback, invalidate, accept, back };
}

export function useVerification(options: VerificationOptions) {
  const state = useVerificationState(options.onProof);
  async function send(values: Record<string, unknown>, resend = false) {
    if (state.feedback.busy) return;
    const target = normalizeContact(String(values.target));
    if (!resend && target === state.recipient && state.challenge) { state.setCurrent(1); return; }
    await state.feedback.run(async () => {
      const payload = contactPayload(target, options);
      state.invalidate();
      const request = state.generation.current;
      const result = await write<{ challenge_id: string }>("/account/verification/send", payload);
      if (request !== state.generation.current) return;
      state.setRecipient(target); state.setChallenge(result.challenge_id); state.setCurrent(1);
    });
  }
  async function verify(values: Record<string, unknown>) {
    await state.feedback.run(async () => {
      const request = state.generation.current;
      const proof = await write<Proof>("/account/verification/verify", {
        challenge_id: state.challenge, code: values.code,
      });
      if (request === state.generation.current) state.accept(proof);
    });
  }
  return { ...state, send, verify };
}
