import { useCallback, useState } from "react";
import { Button, Card, List, Popconfirm, Space, Typography } from "antd";
import { setToken } from "../api/client";
import { mall, write } from "./client";
import { ActionForm, Feedback, useLoad, type Page } from "./shared";

type Device = { id: string; device: string; user_agent: string; revoked_at: string | null };

function signedOut() { setToken(null); window.location.assign("/shop/account"); }

export function Security({ mfaEnabled }: { mfaEnabled: boolean }) {
  const [cursor, setCursor] = useState("");
  const loader = useCallback(() => mall<Page<Device>>(`/account/sessions?cursor=${encodeURIComponent(cursor)}`), [cursor]);
  const query = useLoad(loader);
  const [secret, setSecret] = useState("");
  const [codes, setCodes] = useState<string[]>([]);
  const [error, setError] = useState("");
  async function setup() {
    try { const data = await write<{ secret: string }>("/account/mfa/setup", {}); setSecret(data.secret); }
    catch (e) { setError(e instanceof Error ? e.message : "设置失败"); }
  }
  if (codes.length) return <Card title="恢复码仅展示一次，请离线保存">
    {codes.map((code) => <Typography.Paragraph key={code} copyable>{code}</Typography.Paragraph>)}
    <Button onClick={signedOut}>已保存恢复码，重新登录</Button>
  </Card>;
  return <Space direction="vertical" style={{ width: "100%" }}><Feedback error={error || query.error} />
    {!mfaEnabled && <Button onClick={setup}>设置二步验证</Button>}
    {secret && <><Typography.Text copyable>{secret}</Typography.Text>
      <ActionForm label="启用二步验证" fields={[{ name: "totp", label: "验证器验证码" }]}
        submit={async (values) => {
          const data = await write<{ recovery_codes: string[] }>("/account/mfa/enable", values);
          setCodes(data.recovery_codes); setSecret("");
        }} /></>}
    {mfaEnabled && <ActionForm label="关闭二步验证并退出所有设备" fields={[
      { name: "totp", label: "验证器验证码", required: false },
      { name: "recovery_code", label: "或恢复码", kind: "password", required: false },
    ]} submit={async (values) => { await write("/account/mfa/disable", values); signedOut(); }} />}
    <List dataSource={query.data?.items} renderItem={(device) => <List.Item>
      <Typography.Text>{device.device || device.user_agent || "设备"}</Typography.Text>
      <Button disabled={Boolean(device.revoked_at)} onClick={() => {
        void write(`/account/sessions/${device.id}`, {}, { method: "DELETE" }).then(query.reload).catch((e: Error) => setError(e.message));
      }}>下线</Button></List.Item>} />
    {query.data?.next_cursor && <Button onClick={() => setCursor(query.data!.next_cursor!)}>下一页</Button>}
    <Popconfirm title="退出包括本机在内的所有设备？" onConfirm={async () => {
      try { await write("/account/sessions/revoke-all", {}); signedOut(); }
      catch (e) { setError(e instanceof Error ? e.message : "下线失败"); }
    }}><Button danger>全部设备下线</Button></Popconfirm>
  </Space>;
}
