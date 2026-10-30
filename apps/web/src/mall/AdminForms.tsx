import { useState } from "react";
import { Select, Space } from "antd";
import { ActionForm, Feedback, type Row } from "./shared";
import { write } from "./client";
import { StepUp } from "./Verification";

import { OPERATIONS, type Operation } from "./admin-operations";
import { OperationRecordPicker } from "./OperationRecordPicker";
import { operationInitial, operationResource, recordLabel, type OperationResource } from "./operation-records";
import { useRoleChoices } from "./use-role-choices";
import { operationPayload } from "./operation-payload";
import { operationFields } from "./operation-fields";

function OperationForm({ operation, reload, row, resource }: {
  operation: Operation; reload: () => Promise<void>; row?: Row; resource?: OperationResource;
}) {
  const [token, setToken] = useState("");
  const assigningRole = operation.path === "/roles/grant";
  const roles = useRoleChoices(assigningRole);
  async function submit(values: Row) {
    const command = operationPayload({ operation, values, token, record: row });
    await write(command.path, command.body, { method: command.method });
    await reload();
  }
  const fields = operationFields({ operation, row, resource, roles: roles.options });
  return <Space direction="vertical" style={{ width: "100%" }}>
    {assigningRole && <Feedback {...roles} />}
    {operation.purpose && <StepUp purpose={operation.purpose} onToken={setToken} />}
    {(!operation.purpose || token) && <ActionForm label={operation.title} fields={fields} submit={submit} guided
      disabled={assigningRole && (roles.loading || Boolean(roles.error))}
      reviewContext={<p>{row ? `${resource?.label ?? "操作对象"}：${recordLabel(row)}` : operation.title}</p>}
      initial={operationInitial({ operation, resource, row })} />}
  </Space>;
}

function OperationEditor({ operation, permissions, reload }: {
  operation: Operation; permissions: string[]; reload: () => Promise<void>;
}) {
  const [row, setRow] = useState<Row>();
  const resource = operationResource(operation, permissions);
  return <div className="af-work-stack">
    {resource && <OperationRecordPicker resource={resource} selected={row} onSelect={setRow} />}
    {(!resource || row) && <OperationForm key={`${String(row?.id ?? row?.key ?? "new")}:${String(row?.version ?? "")}`}
      operation={operation} reload={reload} resource={resource} row={row} />}
  </div>;
}

export function AdminForms({ module, permissions, reload, revision }: {
  module: string; permissions: string[]; reload: () => Promise<void>; revision: number;
}) {
  const [selected, setSelected] = useState("");
  const operations = (OPERATIONS[module] ?? []).filter((operation) => permissions.includes(operation.permission));
  const operation = operations.find((item) => item.title === selected) ?? operations[0];
  if (!operation) return null;
  return <div className="af-mall-admin-operation-groups"><label className="af-field"><span>选择管理操作</span>
    <Select aria-label="选择管理操作" value={operation.title} onChange={setSelected}
      options={operations.map((item) => ({ value: item.title, label: item.title }))} /></label>
    <OperationEditor key={`${operation.title}:${revision}`} operation={operation} reload={reload} permissions={permissions} />
  </div>;
}

export function hasAdminOperations(module: string, permissions: string[]) {
  return (OPERATIONS[module] ?? []).some((operation) => permissions.includes(operation.permission));
}
