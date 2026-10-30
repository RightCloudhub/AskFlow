import { useState } from "react";
import { Button } from "antd";
import { FlowFrame } from "../components/common/FlowFrame";
import { setToken } from "../api/client";
import { ActionForm } from "./shared";
import { StepUp } from "./StepUp";
import { write } from "./client";
import { confirmPasswordField, PASSWORD_HINT, PASSWORD_RULES, type Field } from "./form-fields";

const FIELDS: Field[] = [
  { name: "old_password", label: "当前密码", kind: "password", autoComplete: "current-password" },
  { name: "new_password", label: "新密码", kind: "password", autoComplete: "new-password", hint: PASSWORD_HINT, rules: PASSWORD_RULES },
  confirmPasswordField("new_password"),
];

export function PasswordSettings() {
  const [current, setCurrent] = useState(0);
  const [token, setTokenValue] = useState("");
  const [busy, setBusy] = useState(false);
  function back() { if (!busy) setCurrent(0); }
  return <FlowFrame titles={["确认身份", "设置新密码"]} current={current} onBack={back} busy={busy}>
    <div hidden={current !== 0}>
      <StepUp purpose="password_change" onToken={setTokenValue} onBusyChange={setBusy} />
      <div className="af-form-flow-actions"><Button type="primary" disabled={!token || busy} onClick={() => setCurrent(1)}>下一步</Button></div>
    </div>
    <div hidden={current !== 1}>
      <p className="af-flow-description">修改后将退出全部设备，请使用新密码重新登录。</p>
      <ActionForm label="修改密码并退出全部设备" guided={false} fields={FIELDS} disabled={!token}
        extra={<Button disabled={busy} onClick={back}>上一步</Button>} onBusyChange={setBusy}
        submit={async (values) => {
          if (!token) throw new Error("请先确认身份。");
          await write("/account/password/change", {
            old_password: values.old_password, new_password: values.new_password, step_up_token: token,
          });
          setToken(null); window.location.assign("/shop/account");
        }} />
    </div>
  </FlowFrame>;
}
