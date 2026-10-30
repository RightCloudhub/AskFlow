import { useId, useRef } from "react";
import { Alert, Button, Typography } from "antd";
import { FlowFrame } from "../components/common/FlowFrame";
import { ActionFeedback } from "../components/common/action-feedback";
import { IMAGE_ACCEPT, IMAGE_RESULT_STEP, IMAGE_STEPS, useImageUpload, type ImageUploadProps } from "./image-upload-state";
import "../styles/image-upload.css";

const BYTES_PER_KIB = 1024;
type ImageState = ReturnType<typeof useImageUpload>;

function ImagePicker({ state }: { state: ImageState }) {
  const input = useRef<HTMLInputElement>(null);
  const hint = useId();
  return <div className="af-flow-success">
    <button type="button" className="af-image-picker" disabled={state.feedback.busy} aria-describedby={hint}
      onClick={() => input.current?.click()} onDragOver={(event) => event.preventDefault()}
      onDrop={(event) => { event.preventDefault(); state.choose(event.dataTransfer.files[0]); }}>
      <strong>{state.file?.name ?? "选择或拖入一张图片"}</strong>
      <span>{state.file ? "点击可重新选择" : "PNG、JPG、GIF 或 WebP"}</span>
    </button>
    <input className="af-image-file-input" ref={input} type="file" accept={IMAGE_ACCEPT} aria-label="选择上传图片" tabIndex={-1}
      disabled={state.feedback.busy} onChange={(event) => {
        const file = event.target.files?.[0];
        if (file) state.choose(file);
        event.target.value = "";
      }} />
    <p id={hint} className="af-mall-note">选择后先预览，确认后上传。文件大小上限由部署配置决定。</p>
    {state.file && <Button disabled={state.feedback.busy} onClick={() => state.choose(undefined)}>移除已选图片</Button>}
  </div>;
}

function ImagePreview({ state, kind }: { state: ImageState; kind: ImageUploadProps["kind"] }) {
  if (!state.url || !state.file) return <p className="af-mall-note">正在准备图片预览…</p>;
  const url = state.url;
  return <div className="af-flow-success">
    <figure className={`af-image-preview af-image-preview--${kind}`}>
      <img key={url} src={url} alt={`待上传的${kind === "avatar" ? "头像" : "商品图片"}`}
        onLoad={() => { state.setDecoded(url); state.setError(""); }}
        onError={() => { state.setDecoded(""); state.setError("无法预览这张图片，请返回选择其他图片。"); }} />
      <figcaption>{kind === "avatar" ? "头像显示预览" : "商品图片预览"}</figcaption>
    </figure>
    <div className="af-form-review"><dl>
      <div><dt>文件名</dt><dd>{state.file.name}</dd></div>
      <div><dt>文件大小</dt><dd>{Math.ceil(state.file.size / BYTES_PER_KIB).toLocaleString("zh-CN")} KB</dd></div>
      <div><dt>确认后</dt><dd>{kind === "avatar" ? "替换当前账号头像。" : "生成可用于商品编辑的图片标识。"}</dd></div>
    </dl></div>
  </div>;
}

function ImageResult({ state, props }: { state: ImageState; props: ImageUploadProps }) {
  return <div className="af-flow-success">
    <Alert type="success" showIcon title={props.kind === "avatar" ? "头像已保存" : "商品图片已上传"} />
    {state.result?.key && <>
      <Typography.Paragraph copyable={{ text: state.result.key }}>图片标识：{state.result.key}</Typography.Paragraph>
      <p className="af-mall-note">复制标识并填入商品的图片字段，保存商品后生效。</p>
    </>}
    <div className="af-form-flow-actions">
      {props.kind === "catalog" && <Button disabled={state.feedback.busy} onClick={state.restart}>再上传一张</Button>}
      {props.reload && <Button loading={state.feedback.busy} onClick={() => void state.feedback.run(props.reload!)}>刷新账号资料</Button>}
      {props.onCancel && <Button disabled={state.feedback.busy} onClick={props.onCancel}>完成</Button>}
    </div>
  </div>;
}

export function ImageUploadFlow(props: ImageUploadProps) {
  const state = useImageUpload(props);
  const result = state.current === IMAGE_RESULT_STEP;
  return <FlowFrame titles={IMAGE_STEPS} current={state.current} onBack={state.back} busy={state.feedback.busy}
    backDisabled={result} focusOnMount={props.kind === "avatar"}>
    <div hidden={state.current !== 0}><ImagePicker state={state} /></div>
    {state.current === 1 && <ImagePreview state={state} kind={props.kind} />}
    {result && <ImageResult state={state} props={props} />}
    {state.error && <Alert type="error" showIcon title={state.error} role="alert" />}
    <ActionFeedback state={state.feedback} />
    {!result && <div className="af-form-flow-actions">
      {state.current > 0 && <Button disabled={state.feedback.busy} onClick={() => state.back(0)}>上一步</Button>}
      {props.onCancel && <Button disabled={state.feedback.busy} onClick={props.onCancel}>取消更换</Button>}
      {state.current === 0
        ? <Button type="primary" disabled={!state.file || Boolean(state.error)} onClick={() => state.setCurrent(1)}>下一步</Button>
        : <Button type="primary" loading={state.feedback.busy} disabled={!state.ready || Boolean(state.error)} onClick={() => void state.upload()}>
          {props.kind === "avatar" ? "确认保存头像" : "确认上传图片"}</Button>}
    </div>}
  </FlowFrame>;
}
