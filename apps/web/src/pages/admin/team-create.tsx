import { useState } from "react";
import { Button, Form, Input, Select } from "antd";
import type { Team } from "../../api/types";
import { INTENT_LABELS } from "../../components/admin/labels";
import { SettingsSection } from "../../components/admin/workspace";
import { GuidedForm } from "../../components/common/GuidedForm";
import { useCreateTeam } from "../../hooks/use-ops";

const BUSINESS_OPTIONS = ["faq", "product", "order_query", "fault_report", "complaint", "handoff"]
  .map((value) => ({ value, label: INTENT_LABELS[value] }));

export function TeamCreate({ onAddMembers }: { onAddMembers: (team: Team) => void }) {
  const [form] = Form.useForm();
  const [created, setCreated] = useState<Team>();
  const mutation = useCreateTeam();
  async function create(values: Record<string, unknown>) {
    const scope = values.scope as string[];
    setCreated(await mutation.mutateAsync({ name: String(values.name).trim(), scope: scope.join(",") }));
  }
  return <SettingsSection title="新建技能组" description="确定名称和负责业务，建组后继续添加座席成员。">
    <GuidedForm form={form} onFinish={create} submitLabel="创建技能组" initialValues={{ scope: [] }} resetOnSuccess
      restartLabel="再建一个技能组" onRestart={() => setCreated(undefined)}
      result={created && <div className="af-flow-success"><p>技能组「{created.name}」已创建，可继续添加座席。</p>
        <Button type="primary" onClick={() => onAddMembers(created)}>添加座席成员</Button></div>} steps={[
        { title: "技能组名称", fields: ["name"], content: <Form.Item name="name" label="技能组名称"
          rules={[{ required: true, whitespace: true, message: "请填写技能组名称。" }]}><Input placeholder="例如：售后支持" /></Form.Item> },
        { title: "负责业务", fields: ["scope"], content: <Form.Item name="scope" label="负责业务（可选）">
          <Select mode="multiple" placeholder="选择业务范围" options={BUSINESS_OPTIONS} /></Form.Item> },
      ]} review={(values) => <dl><div><dt>技能组</dt><dd>{String(values.name).trim()}</dd></div>
        <div><dt>负责业务</dt><dd>{(values.scope as string[]).map((value) => INTENT_LABELS[value]).join("、") || "未配置"}</dd></div></dl>} />
  </SettingsSection>;
}
