import type { ReactNode } from "react";
import { Tabs } from "antd";
import { ActionForm, type Row } from "./shared";
import { BindingSettings, PasswordSettings, PrivacySettings } from "./AccountPrivacy";
import { AvatarUpload } from "./AvatarUpload";
import { NotificationPreferences } from "./NotificationPreferences";
import { Addresses } from "./Addresses";
import { Security } from "./AccountSecurity";
import { useFeatures } from "../plugins/features";
import { useSearchParams } from "react-router-dom";

export type Profile = { username: string; email: string; nickname: string; region: string; locale: string; version: number; mfa_enabled: boolean; avatar?: string };
type ProfileQuery = { data?: Profile; reload: () => Promise<void> };

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
  const selected = params.get("section") ?? "profile";
  const sections = ["profile", "security", "addresses", "password", "bindings", "privacy", ...(enabled("mall_notify") ? ["notifications"] : [])];
  return <Tabs activeKey={sections.includes(selected) ? selected : "profile"}
    onChange={(section) => setParams((current) => { current.set("section", section); return current; }, { replace: true })} items={[
    { key: "profile", label: "个人资料", children: <ProfilePane query={query} update={update} /> },
    { key: "security", label: "安全与设备", children: <SettingsPane title="登录安全" description="管理二步验证和已登录设备。">
      <Security mfaEnabled={query.data?.mfa_enabled ?? false} /></SettingsPane> },
    { key: "addresses", label: "收货地址", children: <SettingsPane title="收货地址" description="添加或编辑收货信息，选择常用的默认地址。"><Addresses /></SettingsPane> },
    { key: "password", label: "修改密码", children: <SettingsPane title="修改密码" description="验证身份后更新密码，修改完成将退出全部设备。"><PasswordSettings /></SettingsPane> },
    { key: "bindings", label: "联系方式", children: <SettingsPane title="联系方式" description="验证已有和新的联系方式后，完成手机或邮箱换绑。"><BindingSettings /></SettingsPane> },
    { key: "privacy", label: "数据与注销", children: <SettingsPane title="个人数据" description="导出账号资料，或在结清订单与钱包后注销账号。"><PrivacySettings /></SettingsPane> },
    ...(enabled("mall_notify") ? [{ key: "notifications", label: "通知偏好", children: <SettingsPane title="通知偏好"
      description="选择接收订单、退款和钱包通知的方式与时间。"><NotificationPreferences /></SettingsPane> }] : []),
  ]} />;
}
