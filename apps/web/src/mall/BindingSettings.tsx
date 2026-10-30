import { useState } from "react";
import { Button, Radio } from "antd";
import { FlowFrame } from "../components/common/FlowFrame";
import { ActionFeedback, useActionFeedback } from "../components/common/action-feedback";
import { StepUp } from "./StepUp";
import { Verification, type Proof } from "./Verification";
import { write } from "./client";

const TITLES = ["验证原联系方式", "验证新联系方式", "确认身份", "核对变更"];
const REVIEW_STEP = TITLES.length - 1;

function useBindingFlow() {
  const [current, setCurrent] = useState(0);
  const [channel, setChannel] = useState<"sms" | "email">("sms");
  const [oldProof, setOldProof] = useState<Proof>();
  const [newProof, setNewProof] = useState<Proof>();
  const [token, setToken] = useState("");
  const [contacts, setContacts] = useState({ old: "", new: "" });
  const [childBusy, setChildBusy] = useState(false);
  const feedback = useActionFeedback();
  const busy = feedback.busy || childBusy;
  function changeChannel(next: "sms" | "email") {
    setChannel(next); setOldProof(undefined); setNewProof(undefined); setToken("");
    setContacts({ old: "", new: "" }); feedback.clear();
  }
  function accept(kind: "old" | "new", proof?: Proof, recipient = "") {
    if (kind === "old") setOldProof(proof); else setNewProof(proof);
    setToken(""); feedback.clear();
    setContacts((previous) => ({ ...previous, [kind]: recipient }));
  }
  function back(index: number) {
    if (!busy && index >= 0 && index < current) { setCurrent(index); feedback.clear(); }
  }
  async function save() {
    if (!oldProof || !newProof || !token) return;
    await feedback.run(async () => {
      await write("/account/bindings/change", { channel, old: oldProof, new: newProof, step_up_token: token });
      window.location.reload();
    });
  }
  const ready = [Boolean(oldProof), Boolean(newProof), Boolean(token), Boolean(oldProof && newProof && token)];
  return { current, channel, contacts, oldProof, newProof, busy, ready, feedback, changeChannel, accept, back, save,
    setChildBusy, setToken, next: () => { if (!busy && ready[current]) setCurrent(current + 1); } };
}

export function BindingSettings() {
  const state = useBindingFlow();
  const review = state.current === REVIEW_STEP;
  return <FlowFrame titles={TITLES} current={state.current} busy={state.busy} onBack={state.back}>
    <div hidden={state.current !== 0}>
      <label className="af-field"><span>更换联系方式</span>
        <Radio.Group aria-label="更换联系方式" value={state.channel} disabled={state.busy}
          options={[{ value: "sms", label: "手机号" }, { value: "email", label: "邮箱" }]}
          onChange={(event) => state.changeChannel(event.target.value)} /></label>
      <Verification key={`old:${state.channel}`} purpose="bind-old" channel={state.channel} compact
        onProof={(proof, recipient) => state.accept("old", proof, recipient)} onBusyChange={state.setChildBusy} />
    </div>
    <div hidden={state.current !== 1}>
      <Verification key={`new:${state.channel}`} purpose="bind-new" channel={state.channel} compact
        onProof={(proof, recipient) => state.accept("new", proof, recipient)} onBusyChange={state.setChildBusy} />
    </div>
    <div hidden={state.current !== 2}>
      <StepUp key={`${state.oldProof?.verification_id}:${state.newProof?.verification_id}`} purpose="binding_change"
        onToken={state.setToken} onBusyChange={state.setChildBusy} />
    </div>
    {review && <div className="af-form-review"><dl>
      <div><dt>变更内容</dt><dd>更换账号绑定的{state.channel === "sms" ? "手机号" : "邮箱"}</dd></div>
      <div><dt>原联系方式</dt><dd>{state.contacts.old}</dd></div>
      <div><dt>新联系方式</dt><dd>{state.contacts.new}</dd></div>
      <div><dt>验证结果</dt><dd>原联系方式、新联系方式和账号身份均已验证。</dd></div>
    </dl><p>保存后请使用新联系方式登录和接收验证码。</p></div>}
    <ActionFeedback state={state.feedback} />
    <div className="af-form-flow-actions">
      {state.current > 0 && <Button disabled={state.busy} onClick={() => state.back(state.current - 1)}>上一步</Button>}
      <Button type="primary" disabled={state.busy || !state.ready[state.current]} loading={state.feedback.busy}
        onClick={() => review ? void state.save() : state.next()}>{review ? "保存联系方式" : "下一步"}</Button>
    </div>
  </FlowFrame>;
}
