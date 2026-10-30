import { useEffect, useState } from "react";
import { Button, Form, Input } from "antd";
import { useNavigate, useSearchParams } from "react-router-dom";
import { GuidedForm } from "../../components/common/GuidedForm";
import { ActionFeedback, useActionFeedback } from "../../components/common/action-feedback";
import { authService } from "../../services/auth-service";
import { setToken } from "../../api/client";
import { loginReturnPath } from "./return-path";
import { readAuthError } from "./use-login-form";

const USERNAME_MIN = 3;
const PASSWORD_MIN = 8;
const REQUIRED = [{ required: true, whitespace: true, message: "请填写此项。" }];
type Credentials = { username: string; password: string };

async function createAccount(values: Record<string, unknown>) {
  try {
    await authService.register(String(values.username).trim(), String(values.email).trim(), String(values.password));
  } catch (error) { throw new Error(readAuthError(error, "register")); }
}

function RegistrationFields() {
  return <>
    <Form.Item name="password" label="密码" extra="至少 8 位" rules={[...REQUIRED, { min: PASSWORD_MIN, message: "密码至少需要 8 位。" }]}>
      <Input.Password autoComplete="new-password" />
    </Form.Item>
    <Form.Item name="confirmation" label="确认密码" dependencies={["password"]} rules={[
      ...REQUIRED, ({ getFieldValue }) => ({ validator: (_, value) => !value || value === getFieldValue("password")
        ? Promise.resolve() : Promise.reject(new Error("两次输入的密码不一致。")) }),
    ]}><Input.Password autoComplete="new-password" /></Form.Item>
  </>;
}

export function RegisterForm({ onBusyChange }: { onBusyChange: (busy: boolean) => void }) {
  const [form] = Form.useForm();
  const [created, setCreated] = useState<Credentials>();
  const feedback = useActionFeedback();
  useEffect(() => { onBusyChange(feedback.busy); }, [feedback.busy, onBusyChange]);
  const navigate = useNavigate();
  const [params] = useSearchParams();
  async function signIn(credentials: Credentials) {
    await feedback.run(async () => {
      const token = await authService.login(credentials.username, credentials.password);
      setToken(token.access_token); navigate(loginReturnPath(params.get("next"), "/"), { replace: true });
    });
  }
  async function submit(values: Record<string, unknown>) {
    const credentials = { username: String(values.username).trim(), password: String(values.password) };
    const saved = await feedback.run(() => createAccount(values));
    if (!saved) return false;
    setCreated(credentials);
    await signIn(credentials);
    return true;
  }
  if (created) return <div className="af-flow-success"><h3 className="af-form-step-title">账号已创建</h3>
    <p>使用新账号继续进入 AskFlow。</p><ActionFeedback state={feedback} />
    <Button type="primary" loading={feedback.busy} onClick={() => void signIn(created)}>登录并继续</Button>
  </div>;
  return <GuidedForm form={form} onFinish={submit} submitLabel="创建账号并登录" onValuesChange={feedback.clear}
    feedback={<ActionFeedback state={feedback} />} steps={[
      { title: "账号信息", description: "填写用户名和用于联系您的邮箱。", fields: ["username", "email"], content: <>
        <Form.Item name="username" label="用户名" extra="至少 3 个字符" rules={[...REQUIRED, { min: USERNAME_MIN, message: "用户名至少需要 3 个字符。" }]}>
          <Input autoComplete="username" /></Form.Item>
        <Form.Item name="email" label="邮箱" rules={[...REQUIRED, { type: "email", message: "请输入有效邮箱。" }]}>
          <Input type="email" autoComplete="email" /></Form.Item>
      </> },
      { title: "设置密码", fields: ["password", "confirmation"], content: <RegistrationFields /> },
    ]} review={(values) => <dl><div><dt>用户名</dt><dd>{String(values.username)}</dd></div>
      <div><dt>邮箱</dt><dd>{String(values.email)}</dd></div><div><dt>密码</dt><dd>已设置</dd></div></dl>} />;
}
