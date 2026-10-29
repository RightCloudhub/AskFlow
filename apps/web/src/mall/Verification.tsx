import { useState } from "react";
import { Space } from "antd";
import { write } from "./client";
import { ActionForm, type Row } from "./shared";
import { DemoCode } from "./DemoCode";

export type Proof = { verification_id: string; verification_token: string };

export function Verification({ purpose, onProof }: { purpose: string; onProof: (proof: Proof) => void }) {
  const [challenge, setChallenge] = useState("");
  async function send(values: Row) {
    const target = String(values.target);
    const response = await write<{ challenge_id: string }>("/account/verification/send", {
      target, channel: target.startsWith("+") ? "sms" : "email", purpose,
    });
    setChallenge(response.challenge_id);
  }
  return <Space direction="vertical" style={{ width: "100%" }}>
    <ActionForm label="发送验证码" submit={send} fields={[{ name: "target", label: "邮箱或国际格式手机号" }]} />
    {challenge && <DemoCode challenge={challenge} />}
    {challenge && <ActionForm label="验证" fields={[{ name: "code", label: "验证码" }]}
      submit={async (values) => onProof(await write<Proof>("/account/verification/verify", { challenge_id: challenge, code: values.code }))} />}
  </Space>;
}

export function StepUp({ purpose, onToken }: { purpose: string; onToken: (token: string) => void }) {
  const [proof, setProof] = useState<Proof>();
  async function verify(values: Row) {
    const response = await write<{ step_up_token: string }>("/account/step-up", { ...values, ...proof, purpose });
    onToken(response.step_up_token);
  }
  return <Space direction="vertical" style={{ width: "100%" }}>
    <Verification purpose="step-up" onProof={setProof} />
    <ActionForm label="确认身份" submit={verify} fields={[
      { name: "totp", label: "已开启二步验证时输入验证器验证码", required: false },
      { name: "recovery_code", label: "或一次性恢复码", kind: "password", required: false },
    ]} />
  </Space>;
}
