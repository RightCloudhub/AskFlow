import { Alert, Button, Segmented } from "antd";
import { AuthFields } from "./login-parts";
import { AuthFrame } from "./auth-frame";
import { useLoginForm } from "./use-login-form";

export function LoginPage() {
  const state = useLoginForm();
  const login = state.mode === "login";
  return <AuthFrame title={login ? "登录 AskFlow" : "创建您的账号"}
    description={login ? "登录后继续咨询，或进入管理控制台。" : "创建账号，开始您的第一段服务对话。"}>
    <form onSubmit={(event) => void state.submit(event)} className="af-auth-form">
      <Segmented block value={state.mode} onChange={(value) => {
        state.setMode(value as "login" | "register"); state.setError(null);
      }} options={[{ label: "登录", value: "login" }, { label: "注册", value: "register" }]} />
      <AuthFields state={state} />
      {state.error && <Alert type="error" showIcon title={state.error} />}
      <Button type="primary" htmlType="submit" size="large" block loading={state.loading}>
        {login ? "登录并继续" : "创建账号并登录"}
      </Button>
    </form>
  </AuthFrame>;
}
