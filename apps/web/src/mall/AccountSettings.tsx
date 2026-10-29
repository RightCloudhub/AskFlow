import { useCallback } from "react";
import { Button, Card, Descriptions, Tabs } from "antd";
import { logoutMallSession } from "./session";
import { mall, write } from "./client";
import { ActionForm, Feedback, useLoad, type Row } from "./shared";
import { BindingSettings, PasswordSettings, PrivacySettings } from "./AccountPrivacy";
import { AvatarUpload } from "./AvatarUpload";
import { NotificationPreferences } from "./NotificationPreferences";
import { useFeatures } from "../plugins/features";
import { Addresses } from "./Addresses";
import { Security } from "./AccountSecurity";

type Profile = { username: string; email: string; nickname: string; region: string; locale: string; version: number; mfa_enabled: boolean };

export function AccountSettings() {
  const { enabled } = useFeatures();
  const loader = useCallback(() => mall<Profile>("/account/profile"), []);
  const query = useLoad(loader);
  async function update(values: Row) {
    await write("/account/profile", { ...values, expected_version: query.data?.version }, { method: "PATCH" });
    await query.reload();
  }
  return <Card title="账号设置"><Feedback {...query} />
    <Tabs items={[
      { key: "profile", label: "个人资料", children: <>
        <Descriptions items={[{ key: "email", label: "邮箱", children: query.data?.email }]} />
        <AvatarUpload reload={query.reload} />
        {query.data && <ActionForm key={query.data.version} label="保存资料" initial={query.data} submit={update} fields={[
          { name: "nickname", label: "昵称" }, { name: "region", label: "地区", required: false },
          { name: "locale", label: "语言（zh-CN / en-US）" },
        ]} />}</> },
      { key: "security", label: "安全与设备", children: <Security mfaEnabled={query.data?.mfa_enabled ?? false} /> },
      { key: "addresses", label: "收货地址", children: <Addresses /> },
      { key: "password", label: "修改密码", children: <PasswordSettings /> },
      { key: "bindings", label: "联系方式", children: <BindingSettings /> },
      { key: "privacy", label: "数据与注销", children: <PrivacySettings /> },
      ...(enabled("mall_notify") ? [{ key: "notifications", label: "通知偏好", children: <NotificationPreferences /> }] : []),
    ]} />
    <Button onClick={async () => {
      await logoutMallSession();
      window.location.assign("/shop/account");
    }}>退出登录</Button>
  </Card>;
}
