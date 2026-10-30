import { useCallback } from "react";
import { Avatar, Button, Tag } from "antd";
import { logoutMallSession } from "./session";
import { mall, write } from "./client";
import { useLoad, type Row } from "./shared";
import { MallPage, MallPanel } from "./presentation";
import { AccountSections, type Profile } from "./account-sections";
import { ActionFeedback, useActionFeedback } from "../components/common/action-feedback";
import { MallQuery, QueryRefresh } from "./query-view";

export function AccountSettings() {
  const loader = useCallback(() => mall<Profile>("/account/profile"), []);
  const query = useLoad(loader);
  const feedback = useActionFeedback();
  async function update(values: Row) {
    await write("/account/profile", { ...values, expected_version: query.data?.version }, { method: "PATCH" });
    await query.reload();
    feedback.succeed("个人资料已更新。");
  }
  return <MallPage title="账号设置" description="管理个人资料、收货地址与账号安全。"
    actions={<QueryRefresh query={query} />}>
    <ActionFeedback state={feedback} /><MallQuery query={query}>
    {query.data && <><div className="af-mall-account-profile"><div>
      <div className="af-account-person"><Avatar className="af-avatar" src={query.data.avatar}>{(query.data.nickname || query.data.username).slice(0, 1)}</Avatar>
        <h2>{query.data.nickname || query.data.username}</h2></div><p>{query.data.email || "尚未绑定邮箱"}</p>
    </div><Tag>{query.data.mfa_enabled ? "二步验证已开启" : "二步验证未开启"}</Tag></div>
      <MallPanel title="账号管理"><AccountSections query={query} update={update} /></MallPanel></>}
    </MallQuery><div className="af-account-signout"><Button loading={feedback.busy} onClick={() => void feedback.run(async () => {
      await logoutMallSession(); window.location.assign("/shop/account");
    })}>退出登录</Button></div>
  </MallPage>;
}
