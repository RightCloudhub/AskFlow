import { useCallback, useState } from "react";
import { Alert, Button, Checkbox, Collapse, List, Popconfirm, Tag, Typography } from "antd";
import { setToken } from "../api/client";
import { mall, write } from "./client";
import { ActionForm, useLoad, type Page, type Row } from "./shared";
import { ActionFeedback, useActionFeedback } from "../components/common/action-feedback";
import { CursorNav, MallQuery, QueryRefresh, useCursor } from "./query-view";
import { formatDate } from "./presentation";

type Device = { id: string; device: string; user_agent: string; revoked_at: string | null; last_active?: string };
function signedOut() { setToken(null); window.location.assign("/shop/account"); }

function RecoveryCodes({ codes }: { codes: string[] }) {
  const [saved, setSaved] = useState(false);
  return <section className="af-security-block"><h3>保存恢复码</h3>
    <Alert type="warning" showIcon title="恢复码仅展示一次" description="每个恢复码仅可使用一次。请离线保存，验证器不可用时可用于登录。" />
    <div className="af-recovery-codes">{codes.map((code) => <Typography.Paragraph key={code} copyable={{ text: code }}><code>{code}</code></Typography.Paragraph>)}</div>
    <Checkbox checked={saved} onChange={(event) => setSaved(event.target.checked)}>我已保存恢复码</Checkbox>
    <Button type="primary" disabled={!saved} onClick={signedOut}>完成设置，重新登录</Button>
  </section>;
}

function MfaSettings({ enabled }: { enabled: boolean }) {
  const [secret, setSecret] = useState("");
  const [codes, setCodes] = useState<string[]>([]);
  const feedback = useActionFeedback();
  async function setup() {
    const data = await write<{ secret: string }>("/account/mfa/setup", {});
    setSecret(data.secret);
  }
  async function disable(values: Row) {
    if (!values.totp && !values.recovery_code) throw new Error("请输入验证器验证码或一个恢复码。");
    await write("/account/mfa/disable", values); signedOut();
  }
  if (codes.length) return <RecoveryCodes codes={codes} />;
  return <section className="af-security-block"><div className="af-security-heading"><h3>二步验证</h3><Tag>{enabled ? "已开启" : "未开启"}</Tag></div>
    <p className="af-mall-note">开启后，登录需要密码和验证器验证码。请保留恢复码以备验证器不可用。</p>
    <ActionFeedback state={feedback} />
    {!enabled && !secret && <Button loading={feedback.busy} onClick={() => void feedback.run(setup)}>设置二步验证</Button>}
    {secret && <div className="af-security-setup"><p className="af-mall-note">将下方密钥添加至验证器，再填写生成的验证码。</p>
      <Typography.Paragraph copyable={{ text: secret }}><code>{secret}</code></Typography.Paragraph>
      <ActionForm label="启用二步验证" fields={[{ name: "totp", label: "验证器验证码", inputMode: "numeric", autoComplete: "one-time-code" }]}
        submit={async (values) => { const data = await write<{ recovery_codes: string[] }>("/account/mfa/enable", values); setCodes(data.recovery_codes); setSecret(""); }} />
    </div>}
    {enabled && <Collapse ghost items={[{ key: "disable", label: "关闭二步验证", children:
      <><p className="af-mall-note">关闭后将退出全部设备，恢复码也会失效。</p><ActionForm label="关闭验证并退出全部设备" fields={[
        { name: "totp", label: "验证器验证码", required: false, inputMode: "numeric", autoComplete: "one-time-code" },
        { name: "recovery_code", label: "恢复码", kind: "password", required: false, autoComplete: "off", hint: "验证码与恢复码任选一项。" },
      ]} submit={disable} /></> }]} />}
  </section>;
}

function DeviceSessions() {
  const paging = useCursor();
  const loader = useCallback(() => mall<Page<Device>>(`/account/sessions?cursor=${encodeURIComponent(paging.cursor)}`), [paging.cursor]);
  const query = useLoad(loader);
  const feedback = useActionFeedback();
  return <section className="af-security-block"><div className="af-security-heading"><h3>登录设备</h3><QueryRefresh query={query} /></div>
    <ActionFeedback state={feedback} /><MallQuery query={query}>
      <List className="af-device-list" dataSource={query.data?.items} locale={{ emptyText: "暂无登录设备。" }} renderItem={(device) => <List.Item>
        <div className="af-device-identity"><strong>{device.user_agent || device.device || "登录设备"}</strong>
          <span>最近活跃 {formatDate(device.last_active)}</span><span className="af-device-id">设备标识 {device.device || device.id}</span></div>
        {device.revoked_at ? <Tag>已下线</Tag> : <Popconfirm title="让此设备下线？" description="此设备需要重新登录；若为本机，当前会话也将结束。"
          okText="确认下线" cancelText="保留" onConfirm={() => feedback.run(async () => {
            await write(`/account/sessions/${device.id}`, {}, { method: "DELETE" }); await query.reload();
          }, "设备已下线。") }><Button type="text" disabled={feedback.busy}>下线</Button></Popconfirm>}
      </List.Item>} />
    </MallQuery><CursorNav paging={paging} nextCursor={query.data?.next_cursor} loading={query.loading} />
    <Popconfirm title="退出所有登录设备？" description="包括当前设备，操作后需要重新登录。" okText="退出全部" cancelText="保留"
      onConfirm={() => feedback.run(async () => { await write("/account/sessions/revoke-all", {}); signedOut(); })}>
      <Button danger loading={feedback.busy}>退出全部设备</Button>
    </Popconfirm>
  </section>;
}

export function Security({ mfaEnabled }: { mfaEnabled: boolean }) {
  return <div className="af-security-stack"><MfaSettings enabled={mfaEnabled} /><DeviceSessions /></div>;
}
