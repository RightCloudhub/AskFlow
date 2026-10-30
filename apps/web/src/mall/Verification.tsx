import { useEffect, useRef, useState } from "react";
import { write } from "./client";
import { ActionForm, type Row } from "./shared";
import { DemoCode } from "./DemoCode";

export type Proof = { verification_id: string; verification_token: string };
const CONTACT_PATTERN = /^(?:[^\s@]+@[^\s@]+\.[^\s@]+|\+[\d\s()-]+)$/;
const CODE_PATTERN = /^\d{6}$/;

type VerificationProps = { purpose: string; onProof: (proof?: Proof) => void; channel?: "email" | "sms" };

function useProofVerification({ purpose, onProof, channel }: VerificationProps) {
  const [challenge, setChallenge] = useState("");
  const [recipient, setRecipient] = useState("");
  const [verified, setVerified] = useState(false);
  const generation = useRef(0);
  useEffect(() => () => { generation.current += 1; }, []);
  function invalidate() {
    generation.current += 1;
    setChallenge(""); setVerified(false); onProof(undefined);
  }
  async function send(values: Row) {
    const target = String(values.target).trim();
    if (channel === "sms" && !target.startsWith("+")) throw new Error("请填写包含国家区号的手机号。");
    if (channel === "email" && !target.includes("@")) throw new Error("请填写有效的邮箱地址。");
    invalidate();
    const request = generation.current;
    const phone = target.replace(/[\s()-]/g, "");
    const response = await write<{ challenge_id: string }>("/account/verification/send", {
      target: target.startsWith("+") ? phone : target, channel: channel ?? (target.startsWith("+") ? "sms" : "email"), purpose,
    });
    if (request !== generation.current) return;
    setRecipient(target); setChallenge(response.challenge_id);
  }
  async function verify(values: Row) {
    const request = generation.current;
    const proof = await write<Proof>("/account/verification/verify", { challenge_id: challenge, code: values.code });
    if (request !== generation.current) return;
    onProof(proof); setVerified(true);
  }
  return { challenge, recipient, verified, invalidate, send, verify };
}

export function Verification(props: VerificationProps) {
  const { channel } = props;
  const { challenge, recipient, verified, invalidate, send, verify } = useProofVerification(props);
  return <div className="af-verification-stack">
    <ActionForm label={challenge ? "重新发送验证码" : "发送验证码"} submit={send} onChange={invalidate}
      successMessage="验证码已发送，请查看邮箱或短信。" fields={[{
        name: "target", label: channel === "sms" ? "手机号" : channel === "email" ? "邮箱" : "邮箱或手机号", autoComplete: "username",
        hint: channel === "email" ? "填写可正常接收验证码的邮箱。" : "手机号须包含国家区号，如 +86 13800138000。", placeholder: channel === "email" ? "输入邮箱地址" : "邮箱或 +86 手机号",
        rules: [{ pattern: CONTACT_PATTERN, message: "请输入有效邮箱或以 + 开头的国际格式手机号。" }],
      }]} />
    {challenge && <div className="af-verification-code"><p className="af-mall-note">验证码已发往 {recipient}</p>
      <DemoCode key={challenge} challenge={challenge} />
      <ActionForm key={challenge} label={verified ? "已验证" : "验证联系方式"} disabled={verified}
        successMessage="联系方式已验证，可继续下一项操作。" fields={[{ name: "code", label: "验证码",
          inputMode: "numeric", autoComplete: "one-time-code", placeholder: "6 位数字",
          rules: [{ pattern: CODE_PATTERN, message: "请输入 6 位数字验证码。" }],
        }]} submit={verify} />
    </div>}
  </div>;
}

export function StepUp({ purpose, onToken }: { purpose: string; onToken: (token: string) => void }) {
  const [proof, setProof] = useState<Proof>();
  const generation = useRef(0);
  useEffect(() => () => { generation.current += 1; }, []);
  function invalidate() { generation.current += 1; onToken(""); }
  async function verify(values: Row) {
    if (!proof && !values.totp && !values.recovery_code) throw new Error("请先验证联系方式，或填写二步验证码、恢复码中的一项。");
    invalidate();
    const request = generation.current;
    const response = await write<{ step_up_token: string }>("/account/step-up", { ...values, ...proof, purpose });
    if (request !== generation.current) return;
    onToken(response.step_up_token);
  }
  return <div className="af-verification-stack">
    <Verification purpose="step-up" onProof={(next) => { setProof(next); invalidate(); }} />
    <ActionForm label="确认身份" submit={verify} onChange={invalidate}
      successMessage="身份已确认，请继续完成操作。" fields={[
        { name: "totp", label: "二步验证码", required: false, inputMode: "numeric", autoComplete: "one-time-code",
          hint: "已验证联系方式时可留空；也可使用验证器验证码或恢复码确认身份。" },
        { name: "recovery_code", label: "恢复码", kind: "password", required: false, autoComplete: "off" },
      ]} />
  </div>;
}
