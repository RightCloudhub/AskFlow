import { useState } from "react";
import { Button, Collapse, Popconfirm, Select } from "antd";
import { setToken } from "../api/client";
import { mall, write } from "./client";
import { ActionForm, type Row } from "./shared";
import { StepUp, Verification, type Proof } from "./Verification";
import { PASSWORD_HINT, PASSWORD_RULES } from "./form-fields";
import { ActionFeedback, useActionFeedback } from "../components/common/action-feedback";

const DOWNLOAD_URL_LIFETIME_MS = 1000;

export function PasswordSettings() {
  const [token, setTokenValue] = useState("");
  return <div className="af-security-stack"><StepUp purpose="password_change" onToken={setTokenValue} />
    {token && <ActionForm label="修改密码并退出全部设备" fields={[
      { name: "old_password", label: "当前密码", kind: "password", autoComplete: "current-password" },
      { name: "new_password", label: "新密码", kind: "password", autoComplete: "new-password", hint: PASSWORD_HINT, rules: PASSWORD_RULES },
    ]} submit={async (values) => {
      await write("/account/password/change", { ...values, step_up_token: token });
      setToken(null); window.location.assign("/shop/account");
    }} />}
  </div>;
}

export function BindingSettings() {
  const [channel, setChannel] = useState<"sms" | "email">("sms");
  const [oldProof, setOldProof] = useState<Proof>();
  const [newProof, setNewProof] = useState<Proof>();
  const [token, setTokenValue] = useState("");
  const feedback = useActionFeedback();
  function changeChannel(next: "sms" | "email") {
    setChannel(next); setOldProof(undefined); setNewProof(undefined); setTokenValue(""); feedback.clear();
  }
  return <div className="af-security-stack"><label className="af-field"><span>更换联系方式</span>
    <Select aria-label="更换联系方式" value={channel} onChange={changeChannel} disabled={feedback.busy} options={[
      { value: "sms", label: "手机号" }, { value: "email", label: "邮箱" },
    ]} /></label><section className="af-security-block"><h3>验证已有联系方式</h3>
      <Verification key={`old:${channel}`} purpose="bind-old" channel={channel} onProof={(proof) => { setOldProof(proof); setTokenValue(""); }} />
    </section><section className="af-security-block"><h3>验证新联系方式</h3>
      <Verification key={`new:${channel}`} purpose="bind-new" channel={channel} onProof={(proof) => { setNewProof(proof); setTokenValue(""); }} />
    </section><StepUp purpose="binding_change" onToken={setTokenValue} /><ActionFeedback state={feedback} />
    <Button type="primary" loading={feedback.busy} disabled={!oldProof || !newProof || !token} onClick={() => void feedback.run(async () => {
      await write("/account/bindings/change", { channel, old: oldProof, new: newProof, step_up_token: token }); window.location.reload();
    })}>保存联系方式</Button>
  </div>;
}

export function PrivacySettings() {
  const [token, setTokenValue] = useState("");
  const feedback = useActionFeedback();
  async function download() {
    const data = await mall<Row>("/account/export");
    const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: "application/json" }));
    const link = document.createElement("a");
    link.href = url; link.download = "askflow-account.json"; link.click();
    window.setTimeout(() => URL.revokeObjectURL(url), DOWNLOAD_URL_LIFETIME_MS);
  }
  return <div className="af-security-stack"><section className="af-security-block"><h3>导出个人数据</h3>
    <p className="af-mall-note">下载账号资料、订单与资金记录，保存为 JSON 文件。</p>
    <Button loading={feedback.busy} onClick={() => void feedback.run(download, "数据文件已生成，请查看浏览器下载。")}>导出我的数据</Button>
  </section><ActionFeedback state={feedback} /><Collapse items={[{ key: "close", label: "注销账号", children:
    <div className="af-security-stack"><p className="af-mall-note">注销前须结清钱包和未完成订单。注销后个人资料脱敏，财务记录按规定保留。</p>
      <StepUp purpose="account_close" onToken={setTokenValue} />
      <Popconfirm title="确认注销这个账号？" description="完成后将退出当前账号，个人资料将脱敏。" okText="确认注销" cancelText="保留账号"
        onConfirm={() => feedback.run(async () => { await write("/account/close", { step_up_token: token }); setToken(null); window.location.assign("/shop/account"); })}>
        <Button danger disabled={!token} loading={feedback.busy}>注销账号</Button>
      </Popconfirm>
    </div> }]} /></div>;
}
