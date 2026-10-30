import { useState } from "react";
import { Select } from "antd";
import { OPERATIONS } from "./admin-operations";
import { OperationEditor } from "./OperationEditor";

export function AdminForms({ module, permissions, reload }: {
  module: string; permissions: string[]; reload: () => Promise<void>; revision: number;
}) {
  const [selected, setSelected] = useState("");
  const [busy, setBusy] = useState(false);
  const operations = (OPERATIONS[module] ?? []).filter((operation) => permissions.includes(operation.permission));
  const operation = operations.find((item) => item.title === selected) ?? operations[0];
  if (!operation) return null;
  return <div className="af-mall-admin-operation-groups"><label className="af-field"><span>选择管理操作</span>
    <Select aria-label="选择管理操作" value={operation.title} onChange={setSelected} disabled={busy}
      options={operations.map((item) => ({ value: item.title, label: item.title }))} /></label>
    <OperationEditor key={operation.title} operation={operation} reload={reload}
      permissions={permissions} onBusyChange={setBusy} />
  </div>;
}

export function hasAdminOperations(module: string, permissions: string[]) {
  return (OPERATIONS[module] ?? []).some((operation) => permissions.includes(operation.permission));
}
