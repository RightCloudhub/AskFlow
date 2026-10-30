import { Alert, Button, Segmented } from "antd";
import { BrandMark } from "../../components/layout/BrandMark";
import { AuthFields, AuthIntro } from "./login-parts";
import { useLoginForm } from "./use-login-form";

export function LoginPage() {
  const state = useLoginForm();
  return <div className="af-auth"><AuthIntro />
    <main className="af-auth-main">
      <form onSubmit={(event) => void state.submit(event)} className="af-auth-form">
        <div className="af-auth-mobile-brand"><BrandMark /><strong>AskFlow</strong></div>
        <div><h1 className="af-auth-title">{state.mode === "login" ? "登录 AskFlow" : "创建账号"}</h1>
          <p className="af-auth-description">{state.mode === "login" ? "进入客服对话台或管理控制台。" : "注册完成后自动登录。"}</p></div>
        <Segmented block value={state.mode} onChange={(value) => {
          state.setMode(value as "login" | "register"); state.setError(null);
        }} options={[{ label: "登录", value: "login" }, { label: "注册", value: "register" }]} />
        <AuthFields state={state} />
        {state.error && <Alert type="error" showIcon title={state.error} />}
        <Button type="primary" htmlType="submit" size="large" block loading={state.loading}>
          {state.mode === "login" ? "登录" : "注册并登录"}
        </Button>
      </form>
    </main>
  </div>;
}
