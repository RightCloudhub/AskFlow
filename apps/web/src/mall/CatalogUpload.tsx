import { useState } from "react";
import { Button, Space, Typography, Upload } from "antd";
import { mall } from "./client";
import { Feedback } from "./shared";

export function CatalogUpload() {
  const [key, setKey] = useState("");
  const [error, setError] = useState("");
  async function upload(file: File) {
    const form = new FormData(); form.append("file", file);
    try {
      const result = await mall<{ key: string }>("/api/v1/admin/mall/catalog/images", {
        method: "POST", body: form, headers: { "Idempotency-Key": crypto.randomUUID() },
      });
      setKey(result.key); setError("");
    } catch (reason) { setError(reason instanceof Error ? reason.message : "上传失败"); }
    return false as const;
  }
  return <Space direction="vertical"><Upload beforeUpload={upload} showUploadList={false}
    accept="image/png,image/jpeg,image/gif,image/webp"><Button>上传商品图片</Button></Upload>
    {key && <Typography.Text copyable>{key}</Typography.Text>}<Feedback error={error} />
  </Space>;
}
