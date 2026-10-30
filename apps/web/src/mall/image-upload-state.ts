import { useEffect, useRef, useState } from "react";
import { useActionFeedback } from "../components/common/action-feedback";
import { mall } from "./client";

export type ImageUploadResult = { key?: string; avatar?: string };
export type ImageUploadProps = {
  kind: "catalog" | "avatar";
  reload?: () => Promise<void>;
  onUploaded?: (result: ImageUploadResult) => void;
  onCancel?: () => void;
};
export const IMAGE_ACCEPT = "image/png,image/jpeg,image/gif,image/webp";
const IMAGE_TYPES = new Set(IMAGE_ACCEPT.split(","));
const PATHS = { catalog: "/api/v1/admin/mall/catalog/images", avatar: "/account/avatar" };
export const IMAGE_STEPS = ["选择图片", "预览确认", "上传结果"];
export const IMAGE_RESULT_STEP = IMAGE_STEPS.length - 1;

function useImageSelection() {
  const [file, setFile] = useState<File>();
  const [preview, setPreview] = useState<{ file: File; url: string }>();
  const [decoded, setDecoded] = useState("");
  const [error, setError] = useState("");
  useEffect(() => {
    if (!file) { setPreview(undefined); return; }
    const url = URL.createObjectURL(file);
    setPreview({ file, url });
    return () => URL.revokeObjectURL(url);
  }, [file]);
  function select(next?: File) {
    setDecoded(""); setError("");
    if (next && (!IMAGE_TYPES.has(next.type) || !next.size)) {
      setFile(undefined); setError("请选择非空的 PNG、JPG、GIF 或 WebP 图片。");
      return;
    }
    setFile(next);
  }
  const url = preview?.file === file ? preview?.url : undefined;
  return { file, url, error, select, setDecoded, setError, ready: Boolean(url && decoded === url) };
}

export function useImageUpload(props: ImageUploadProps) {
  const selection = useImageSelection();
  const [current, setCurrent] = useState(0);
  const [result, setResult] = useState<ImageUploadResult>();
  const key = useRef(crypto.randomUUID());
  const feedback = useActionFeedback();
  function choose(file?: File) {
    if (feedback.busy || result) return;
    selection.select(file); key.current = crypto.randomUUID(); feedback.clear();
  }
  function back(index: number) {
    if (!feedback.busy && !result && index < current) { setCurrent(index); feedback.clear(); }
  }
  async function upload() {
    const file = selection.file;
    if (!file || !selection.ready || result) return;
    await feedback.run(async () => {
      const body = new FormData();
      body.append("file", file);
      const data = await mall<ImageUploadResult>(PATHS[props.kind], { method: "POST", body,
        headers: { "Idempotency-Key": key.current } });
      setResult(data); setCurrent(IMAGE_RESULT_STEP);
      props.onUploaded?.(data);
      await props.reload?.();
    });
  }
  function restart() {
    if (feedback.busy) return;
    setResult(undefined); setCurrent(0); selection.select(undefined);
    key.current = crypto.randomUUID(); feedback.clear();
  }
  return { ...selection, current, setCurrent, result, feedback, choose, back, upload, restart };
}
