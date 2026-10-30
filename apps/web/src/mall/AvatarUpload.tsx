import { Avatar, Button, Upload } from "antd";
import { mall } from "./client";
import { ActionFeedback, useActionFeedback } from "../components/common/action-feedback";

const AVATAR_SIZE = 48;
const IMAGE_TYPES = new Set(["image/png", "image/jpeg", "image/gif", "image/webp"]);

export function AvatarUpload({ reload, avatar, name = "" }: { reload: () => Promise<void>; avatar?: string; name?: string }) {
  const feedback = useActionFeedback();
  async function upload(file: File) {
    await feedback.run(async () => {
      if (!IMAGE_TYPES.has(file.type)) throw new Error("请选择 PNG、JPG、GIF 或 WebP 图片。");
      const body = new FormData(); body.append("file", file);
      await mall("/account/avatar", { method: "POST", body, headers: { "Idempotency-Key": crypto.randomUUID() } });
      await reload();
    }, "头像已更新。");
    return false as const;
  }
  return <div className="af-avatar-editor"><div className="af-avatar-editor-row"><Avatar className="af-avatar" size={AVATAR_SIZE} src={avatar}>
    {name.slice(0, 1)}</Avatar><div><Upload accept="image/png,image/jpeg,image/gif,image/webp" beforeUpload={upload}
      disabled={feedback.busy} showUploadList={false}><Button loading={feedback.busy}>更换头像</Button></Upload>
      <p className="af-mall-note">支持 PNG、JPG、GIF、WebP 图片。</p></div></div><ActionFeedback state={feedback} /></div>;
}
