import { useState } from "react";
import { Button, Collapse } from "antd";
import { mall } from "./client";
import type { Row } from "./shared";
import { AccountClosureFlow } from "./AccountClosureFlow";
import { ActionFeedback, useActionFeedback } from "../components/common/action-feedback";

const DOWNLOAD_URL_LIFETIME_MS = 1000;
export { BindingSettings } from "./BindingSettings";
export { PasswordSettings } from "./PasswordSettings";

export function PrivacySettings() {
  const [open, setOpen] = useState(false);
  const [closing, setClosing] = useState(false);
  const feedback = useActionFeedback();
  async function download() {
    const data = await mall<Row>("/account/export");
    const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: "application/json" }));
    const link = document.createElement("a");
    link.href = url; link.download = "askflow-account.json"; link.click();
    window.setTimeout(() => URL.revokeObjectURL(url), DOWNLOAD_URL_LIFETIME_MS);
  }
  return <div className="af-security-stack"><section className="af-security-block"><h3>导出个人数据</h3>
    <p className="af-mall-note">下载账号资料、订单与资金记录，保存为 JSON 文件。</p>
    <Button loading={feedback.busy} onClick={() => void feedback.run(download, "数据文件已生成，请查看浏览器下载。")}>导出我的数据</Button>
  </section><ActionFeedback state={feedback} />
    <Collapse activeKey={open ? ["close"] : []} onChange={(keys) => { if (!closing) setOpen(keys.includes("close")); }}
      items={[{ key: "close", label: "注销账号", children: <AccountClosureFlow active={open} onBusyChange={setClosing} /> }]} />
  </div>;
}
