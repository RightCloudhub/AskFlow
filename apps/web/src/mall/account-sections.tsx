import type { ReactNode } from "react";
import { BellOutlined, EnvironmentOutlined, LockOutlined, MailOutlined, SafetyOutlined, UserOutlined, FileTextOutlined } from "@ant-design/icons";
import { useSearchParams } from "react-router-dom";
import { ActionForm, type Row } from "./shared";
import { BindingSettings, PasswordSettings, PrivacySettings } from "./AccountPrivacy";
import { AvatarUpload } from "./AvatarUpload";
import { NotificationPreferences } from "./NotificationPreferences";
import { Addresses } from "./Addresses";
import { Security } from "./AccountSecurity";
import { useFeatures } from "../plugins/features";

export type Profile = { username: string; email: string; nickname: string; region: string; locale: string; version: number; mfa_enabled: boolean; avatar?: string };
type ProfileQuery = { data?: Profile; reload: () => Promise<void> };

export const ACCOUNT_LABELS: Record<string, string> = {
  profile: "个人资料", security: "安全与设备", addresses: "收货地址", password: "修改密码",
  bindings: "联系方式", privacy: "数据与注销", notifications: "通知偏好",
};

function SettingsPane({ title, description, children }: { title: string; description: string; children: ReactNode }) {
  return <section className="af-settings-pane"><div className="af-settings-pane-copy"><h2>{title}</h2><p>{description}</p></div>
    <div className="af-settings-pane-body">{children}</div></section>;
}

function ProfilePane({ query, update }: { query: ProfileQuery; update: (values: Row) => Promise<void> }) {
  return <SettingsPane title="个人资料" description="更新头像与昵称，维护地区和语言偏好。">
    <AvatarUpload reload={query.reload} avatar={query.data?.avatar} name={query.data?.nickname || query.data?.username} />
    {query.data && <ActionForm key={query.data.version} label="保存资料" initial={query.data} submit={update} fields={[
      { name: "nickname", label: "昵称" }, { name: "region", label: "地区", required: false },
      { name: "locale", label: "语言", kind: "select", options: [
        { value: "zh-CN", label: "简体中文" }, { value: "en-US", label: "English" },
      ] },
    ]} />}
  </SettingsPane>;
}

export function AccountSections({ query, update }: { query: ProfileQuery; update: (values: Row) => Promise<void> }) {
  const { enabled } = useFeatures();
  const [params, setParams] = useSearchParams();
  const sections = [
    { key: "profile", icon: <UserOutlined />, body: <ProfilePane query={query} update={update} /> },
    { key: "security", icon: <SafetyOutlined />, body: <SettingsPane title="登录安全" description="管理二步验证和已登录设备。">
      <Security mfaEnabled={query.data?.mfa_enabled ?? false} /></SettingsPane> },
    { key: "addresses", icon: <EnvironmentOutlined />, body: <SettingsPane title="收货地址" description="维护收货信息，选择常用地址。"><Addresses /></SettingsPane> },
    { key: "password", icon: <LockOutlined />, body: <SettingsPane title="修改密码" description="验证身份后更新密码，修改完成将退出全部设备。"><PasswordSettings /></SettingsPane> },
    { key: "bindings", icon: <MailOutlined />, body: <SettingsPane title="联系方式" description="验证已有和新的联系方式后，完成换绑。"><BindingSettings /></SettingsPane> },
    { key: "privacy", icon: <FileTextOutlined />, body: <SettingsPane title="个人数据" description="导出资料，或在结清订单与钱包后注销账号。"><PrivacySettings /></SettingsPane> },
    ...(enabled("mall_notify") ? [{ key: "notifications", icon: <BellOutlined />, body: <SettingsPane title="通知偏好"
      description="选择接收订单、退款和钱包通知的方式与时间。"><NotificationPreferences /></SettingsPane> }] : []),
  ];
  const selected = sections.find((section) => section.key === params.get("section")) ?? sections[0];
  return <div className="af-account-settings-workspace"><nav className="af-account-section-nav" aria-label="账号设置分类">
    {sections.map((section) => <button key={section.key} type="button" aria-current={section.key === selected.key ? "page" : undefined}
      onClick={() => setParams((current) => { current.set("section", section.key); return current; }, { replace: true })}>
      {section.icon}{ACCOUNT_LABELS[section.key]}</button>)}
    </nav><div key={selected.key}>{selected.body}</div>
  </div>;
}
