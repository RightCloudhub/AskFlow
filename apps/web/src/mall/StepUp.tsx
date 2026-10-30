import { useEffect, useRef, useState } from "react";
import { Alert, Button, Radio } from "antd";
import { Verification, type Proof } from "./Verification";
import { ActionForm, type Row } from "./shared";
import { write } from "./client";
import type { Field } from "./form-fields";

type Method = "contact" | "totp" | "recovery_code";
type StepUpProps = { purpose: string; onToken: (token: string) => void; onBusyChange?: (busy: boolean) => void };
const METHODS = [
  { value: "contact", label: "邮箱或手机" }, { value: "totp", label: "验证器" }, { value: "recovery_code", label: "恢复码" },
];
const FIELDS: Record<Method, Field[]> = {
  contact: [],
  totp: [{ name: "totp", label: "二步验证码", inputMode: "numeric", autoComplete: "one-time-code" }],
  recovery_code: [{ name: "recovery_code", label: "恢复码", kind: "password", autoComplete: "off" }],
};

function useStepUp({ purpose, onToken }: StepUpProps) {
  const [method, setMethod] = useState<Method>("contact");
  const [proof, setProof] = useState<Proof>();
  const [complete, setComplete] = useState(false);
  const [generation, setGeneration] = useState(0);
  const request = useRef(0);
  useEffect(() => () => { request.current += 1; }, []);
  function change(next: Method) {
    request.current += 1; setGeneration(request.current);
    setMethod(next); setProof(undefined); setComplete(false); onToken("");
  }
  function acceptProof(next?: Proof) {
    request.current += 1; setProof(next); onToken("");
  }
  async function verify(values: Row) {
    if (method === "contact" && !proof) throw new Error("请先验证联系方式。");
    const pending = ++request.current;
    onToken("");
    const credentials = method === "contact" ? proof : { [method]: values[method] };
    const response = await write<{ step_up_token: string }>("/account/step-up", { ...credentials, purpose });
    if (request.current !== pending) return;
    onToken(response.step_up_token); setComplete(true);
  }
  return { method, proof, complete, generation, change, acceptProof, verify };
}

export function StepUp(props: StepUpProps) {
  const state = useStepUp(props);
  const [busy, setBusy] = useState(false);
  useEffect(() => { if (state.complete) setBusy(false); }, [state.complete]);
  useEffect(() => { props.onBusyChange?.(busy); }, [busy, props.onBusyChange]);
  if (state.complete) return <div className="af-flow-success">
    <Alert type="success" showIcon title="身份已确认" />
    <Button onClick={() => state.change(state.method)}>重新验证身份</Button>
  </div>;
  return <div className="af-verification-stack">
    <label className="af-field"><span>身份验证方式</span>
      <Radio.Group aria-label="身份验证方式" value={state.method} options={METHODS} disabled={busy}
        onChange={(event) => state.change(event.target.value)} /></label>
    {state.method === "contact" && <Verification key={state.generation} purpose="step-up" compact
      onProof={state.acceptProof} onBusyChange={setBusy} />}
    {(state.method !== "contact" || state.proof) && <ActionForm key={state.method} label="确认身份"
      fields={FIELDS[state.method]} guided={false} submit={state.verify} onBusyChange={setBusy} />}
  </div>;
}
