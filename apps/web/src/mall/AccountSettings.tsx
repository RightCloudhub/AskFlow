import { useCallback } from "react";
import { Button } from "antd";
import { logoutMallSession } from "./session";
import { mall, write } from "./client";
import { Feedback, useLoad, type Row } from "./shared";
import { MallPage, MallPanel } from "./presentation";
import { AccountSections, type Profile } from "./account-sections";

export function AccountSettings() {
  const loader = useCallback(() => mall<Profile>("/account/profile"), []);
  const query = useLoad(loader);
  async function update(values: Row) {
    await write("/account/profile", { ...values, expected_version: query.data?.version }, { method: "PATCH" });
    await query.reload();
  }
  return <MallPage title="账号设置" description="管理个人资料、收货地址与账号安全。">
    <Feedback {...query} />
    {query.data && <><div className="af-mall-account-profile"><div>
      <h2>{query.data.nickname || query.data.username}</h2><p>{query.data.email || "尚未绑定邮箱"}</p>
    </div></div><MallPanel title="账号管理"><AccountSections query={query} update={update} /></MallPanel></>}
    <div className="af-account-signout"><Button onClick={async () => {
      await logoutMallSession(); window.location.assign("/shop/account");
    }}>退出登录</Button></div>
  </MallPage>;
}
