import { useState } from "react";
import { Button, Upload } from "antd";
import { mall } from "./client";
import { Feedback } from "./shared";

export function AvatarUpload({ reload }: { reload: () => Promise<void> }) {
  const [error, setError] = useState("");
  async function upload(file: File) {
    const body = new FormData();
    body.append("file", file);
    try {
      await mall("/account/avatar", { method: "POST", body, headers: { "Idempotency-Key": crypto.randomUUID() } });
      await reload();
    } catch (reason) { setError(reason instanceof Error ? reason.message : "上传失败"); }
    return false as const;
  }
  return <><Upload accept="image/png,image/jpeg,image/gif,image/webp" beforeUpload={upload} showUploadList={false}>
    <Button>上传头像</Button></Upload><Feedback error={error} /></>;
}
