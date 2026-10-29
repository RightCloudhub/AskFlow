import { useState } from "react";
import { Button, Card, Popconfirm, Select, Space, Typography } from "antd";
import { setToken } from "../api/client";
import { mall, write } from "./client";
import { ActionForm, Feedback, type Row } from "./shared";
import { StepUp, Verification, type Proof } from "./Verification";

export function PasswordSettings() {
  const [token, setTokenValue] = useState("");
  return <Space direction="vertical"><StepUp purpose="password_change" onToken={setTokenValue} />
    {token && <ActionForm label="修改密码并退出全部设备" fields={[
      { name: "old_password", label: "当前密码", kind: "password" },
      { name: "new_password", label: "新密码", kind: "password" },
    ]} submit={async (values) => {
      await write("/account/password/change", { ...values, step_up_token: token });
      setToken(null); window.location.assign("/shop/account");
    }} />}</Space>;
}

export function BindingSettings() {
  const [channel, setChannel] = useState("sms");
  const [oldProof, setOldProof] = useState<Proof>();
  const [newProof, setNewProof] = useState<Proof>();
  const [token, setTokenValue] = useState("");
  const [error, setError] = useState("");
  const change = async () => {
    try {
      await write("/account/bindings/change", { channel, old: oldProof, new: newProof, step_up_token: token });
      window.location.reload();
    } catch (reason) { setError(reason instanceof Error ? reason.message : "换绑失败"); }
  };
  return <Space direction="vertical"><Select value={channel} onChange={setChannel} options={[
    { value: "sms", label: "绑定或更换手机" }, { value: "email", label: "绑定或更换邮箱" },
  ]} /><Card title="验证已有联系方式"><Verification purpose="bind-old" onProof={setOldProof} /></Card>
    <Card title="验证新联系方式"><Verification purpose="bind-new" onProof={setNewProof} /></Card>
    <StepUp purpose="binding_change" onToken={setTokenValue} /><Feedback error={error} />
    <Button disabled={!oldProof || !newProof || !token} onClick={() => { void change(); }}>保存联系方式</Button></Space>;
}

export function PrivacySettings() {
  const [token, setTokenValue] = useState("");
  const [error, setError] = useState("");
  async function download() {
    try {
      const data = await mall<Row>("/account/export");
      const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: "application/json" }));
      const link = document.createElement("a");
      link.href = url; link.download = "askflow-account.json"; link.click(); URL.revokeObjectURL(url);
    } catch (reason) { setError(reason instanceof Error ? reason.message : "导出失败"); }
  }
  async function close() {
    try {
      await write("/account/close", { step_up_token: token });
      setToken(null); window.location.assign("/shop/account");
    } catch (reason) { setError(reason instanceof Error ? reason.message : "注销失败"); }
  }
  return <Space direction="vertical"><Button onClick={() => { void download(); }}>导出我的数据</Button>
    <Typography.Text>注销前须结清钱包和未完成订单。财务记录保留，个人资料脱敏。</Typography.Text>
    <StepUp purpose="account_close" onToken={setTokenValue} /><Feedback error={error} />
    <Popconfirm title="确认注销账号？" onConfirm={close}><Button danger disabled={!token}>注销账号</Button></Popconfirm>
  </Space>;
}
