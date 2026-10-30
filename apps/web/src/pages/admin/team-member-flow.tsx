import { Form, Select } from "antd";
import { useState } from "react";
import type { Team } from "../../api/types";
import { labelStatus } from "../../components/admin";
import { QueryFeedback } from "../../components/admin/workspace";
import { GuidedForm } from "../../components/common/GuidedForm";
import { useAddTeamMember } from "../../hooks/use-ops";
import { useUsers } from "../../hooks/use-governance";

export function TeamMemberFlow({ team, onBusyChange }: { team: Team; onBusyChange: (busy: boolean) => void }) {
  const [form] = Form.useForm();
  const users = useUsers();
  const add = useAddTeamMember();
  const [added, setAdded] = useState<string[]>([]);
  const available = (users.data ?? []).filter((user) => !team.member_ids?.includes(user.id) && !added.includes(user.id));
  async function submit(values: Record<string, unknown>) {
    const userId = String(values.user_id);
    if (!available.some((user) => user.id === userId)) throw new Error("该账号已加入或不再可选，请返回上一步重新选择。");
    await add.mutateAsync({ teamId: team.id, userId });
    setAdded((previous) => [...previous, userId]);
  }
  return <><QueryFeedback query={users} /><GuidedForm form={form} onFinish={submit} submitLabel="确认添加成员"
    onBusyChange={onBusyChange} disabled={users.isLoading || users.isError} resetOnSuccess restartLabel="继续添加成员"
    steps={[{ title: "选择座席成员", fields: ["user_id"], description: `为「${team.name}」添加成员。`, content:
      <Form.Item name="user_id" label="账号" rules={[{ required: true, message: "请选择要加入的账号。" }]}>
        <Select showSearch optionFilterProp="label" placeholder="选择账号" notFoundContent="暂无可添加的账号"
          options={available.map((user) => ({ value: user.id, label: `${user.username} · ${labelStatus(user.role)}` }))} />
      </Form.Item> }]} review={(values) => <dl><div><dt>加入技能组</dt><dd>{team.name}</dd></div>
      <div><dt>成员账号</dt><dd>{users.data?.find((user) => user.id === values.user_id)?.username ?? String(values.user_id)}</dd></div></dl>} />
  </>;
}
