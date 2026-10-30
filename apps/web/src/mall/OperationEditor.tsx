import { useEffect, useState } from "react";
import { Button } from "antd";
import { FlowFrame } from "../components/common/FlowFrame";
import { ActionForm, Feedback, type Row } from "./shared";
import { write } from "./client";
import { StepUp } from "./StepUp";
import type { Operation } from "./admin-operations";
import { OperationRecordPicker } from "./OperationRecordPicker";
import { operationInitial, operationResource, recordLabel } from "./operation-records";
import { useRoleChoices } from "./use-role-choices";
import { operationPayload } from "./operation-payload";
import { operationFields } from "./operation-fields";
import { formSteps } from "./form-steps";

type EditorProps = { operation: Operation; permissions: string[]; reload: () => Promise<void>; onBusyChange: (busy: boolean) => void };

function useOperationEditor(props: EditorProps) {
  const [row, setRow] = useState<Row>();
  const [current, setCurrent] = useState(0);
  const [token, setToken] = useState("");
  const [revision, setRevision] = useState(0);
  const [pickerRevision, setPickerRevision] = useState(0);
  const [identityBusy, setIdentityBusy] = useState(false);
  const [formBusy, setFormBusy] = useState(false);
  const busy = identityBusy || formBusy;
  useEffect(() => { props.onBusyChange(busy); }, [busy, props.onBusyChange]);
  const resource = operationResource(props.operation, props.permissions);
  const prefix = [resource ? `选择${resource.label}` : "", props.operation.purpose ? "确认身份" : ""].filter(Boolean);
  function select(next?: Row) {
    if (busy) return;
    setRow(next); setToken(""); setRevision((value) => value + 1);
  }
  function back(index: number) { if (!busy && index >= 0 && index < current) setCurrent(index); }
  const ready = current === 0 && resource ? Boolean(row) : Boolean(token);
  function next() { if (!busy && ready) setCurrent(current + 1); }
  async function submit(values: Row) {
    if (props.operation.purpose && !token) throw new Error("请返回上一步确认身份。");
    const command = operationPayload({ operation: props.operation, values, token, record: row });
    await write(command.path, command.body, { method: command.method });
    await props.reload();
  }
  function restart() {
    setCurrent(0); setRow(undefined); setToken(""); setRevision((value) => value + 1);
    setPickerRevision((value) => value + 1);
  }
  return { row, current, resource, prefix, revision, busy, ready, select, back, next, submit,
    token, setToken, setIdentityBusy, setFormBusy, restart, pickerRevision };
}

type EditorState = ReturnType<typeof useOperationEditor>;

function operationContext(state: EditorState, title: string) {
  return state.row ? `${state.resource?.label ?? "操作对象"}：${recordLabel(state.row)}` : title;
}

function OperationPreparation({ state, titles, purpose }: { state: EditorState; titles: string[]; purpose?: string }) {
  const preparing = state.current < state.prefix.length;
  const identityStep = state.prefix.length - 1;
  if (!state.prefix.length) return null;
  return <div hidden={!preparing}><FlowFrame titles={titles} active={preparing}
    current={Math.min(state.current, state.prefix.length - 1)} onBack={state.back} busy={state.busy}>
    <div hidden={state.current !== 0}>
      {state.resource && <OperationRecordPicker key={state.pickerRevision} resource={state.resource} selected={state.row}
        onSelect={state.select} disabled={state.busy} />}
    </div>
    <div hidden={state.current !== identityStep}>
      {purpose && <StepUp key={state.revision} purpose={purpose} onToken={state.setToken} onBusyChange={state.setIdentityBusy} />}
    </div>
    <div className="af-form-flow-actions">
      {state.current > 0 && <Button disabled={state.busy} onClick={() => state.back(state.current - 1)}>上一步</Button>}
      <Button type="primary" disabled={state.busy || !state.ready} onClick={state.next}>下一步</Button>
    </div>
  </FlowFrame></div>;
}

export function OperationEditor(props: EditorProps) {
  const state = useOperationEditor(props);
  const { operation } = props;
  const assigningRole = operation.path === "/roles/grant";
  const roles = useRoleChoices(assigningRole);
  const fields = operationFields({ operation, row: state.row, resource: state.resource, roles: roles.options });
  const titles = [...state.prefix, ...formSteps(fields).map((step) => step.title), "核对提交", "操作结果"];
  const preparing = state.current < state.prefix.length;
  const unavailable = assigningRole && (roles.loading || Boolean(roles.error));
  return <div className="af-work-stack"><OperationPreparation state={state} titles={titles} purpose={operation.purpose} />
    {(!state.resource || state.row) && <div hidden={preparing}>
      {assigningRole && <Feedback {...roles} />}
      <ActionForm key={state.revision} label={operation.title} fields={fields} submit={state.submit} guided
        onRestart={state.restart} restartLabel="开始下一次操作"
        onBusyChange={state.setFormBusy} prefix={{ titles: state.prefix, onBack: state.back }} active={!preparing}
        disabled={(Boolean(operation.purpose) && !state.token) || unavailable}
        reviewContext={<p>{operationContext(state, operation.title)}</p>}
        initial={operationInitial({ operation, resource: state.resource, row: state.row })} />
    </div>}
  </div>;
}
