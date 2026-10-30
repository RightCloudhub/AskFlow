import { useState } from "react";
import { Button, Input, Select } from "antd";
import type { ColumnsType } from "antd/es/table";
import { PageHeader, labelStatus } from "../../components/admin";
import { DataTable, FilterBar, QueryFeedback, RefreshButton, SettingsSection, WorkspacePanel } from "../../components/admin/workspace";
import { useRecordFilter } from "../../components/admin/use-record-filter";
import { ActionFeedback, useActionFeedback } from "../../components/common/action-feedback";
import { useAddTeamMember, useCreateTeam, useTeams } from "../../hooks/use-ops";
import { useUsers } from "../../hooks/use-governance";
import type { Team, User } from "../../api/types";

type MemberActions = { users: User[]; busy: boolean; add: (teamId: string, userId: string) => Promise<unknown> };

function teamColumns(actions: MemberActions): ColumnsType<Team> {
  return [
    { title: "技能组", dataIndex: "name", render: (name, row) =>
      <div className="af-record-title"><strong>{name}</strong><small>{row.description || "未填写说明"}</small></div> },
    { title: "意图范围", dataIndex: "intent_scope", render: (value) => value || "未配置" },
    { title: "成员数", dataIndex: "member_count", align: "right", render: (value, row) => value ?? row.member_ids?.length ?? "—" },
    { title: "添加成员", key: "add", render: (_, row) => <Select aria-label={"为 " + row.name + " 添加成员"}
      placeholder="选择账号加入" showSearch optionFilterProp="label" value={undefined} className="af-team-member-select"
      disabled={actions.busy || !actions.users.length} notFoundContent="暂无可添加的账号"
      options={actions.users.filter((user) => !row.member_ids?.includes(user.id)).map((user) => ({
        value: user.id, label: user.username + " · " + labelStatus(user.role),
      }))} onChange={(id: string) => void actions.add(row.id, id)} /> },
  ];
}

function TeamCreate() {
  const [name, setName] = useState("");
  const [scope, setScope] = useState("");
  const mutation = useCreateTeam();
  const feedback = useActionFeedback();
  async function create() {
    if (!name.trim()) return;
    const done = await feedback.run(() => mutation.mutateAsync({ name: name.trim(), scope: scope.trim() }), "技能组已创建。");
    if (done) { setName(""); setScope(""); }
  }
  return <SettingsSection title="新建技能组" description="按业务能力组织座席，填写这个组负责的意图范围。">
    <ActionFeedback state={feedback} /><form onSubmit={(event) => { event.preventDefault(); void create(); }}>
      <label className="af-field"><span>技能组名称</span><Input value={name} onChange={(event) => setName(event.target.value)}
        placeholder="例如：售后支持" required disabled={feedback.busy} /></label>
      <label className="af-field"><span>意图范围（可选）</span><Input value={scope} onChange={(event) => setScope(event.target.value)}
        placeholder="例如：complaint,fault_report" disabled={feedback.busy} aria-describedby="af-team-scope-hint" />
        <small id="af-team-scope-hint">多个意图代码用英文逗号分隔。</small></label>
      <Button type="primary" htmlType="submit" loading={feedback.busy} disabled={!name.trim()}>创建技能组</Button>
    </form>
  </SettingsSection>;
}

export function TeamsPage() {
  const query = useTeams();
  const users = useUsers();
  const add = useAddTeamMember();
  const feedback = useActionFeedback();
  const filter = useRecordFilter({ rows: query.data ?? [], fields: ["name", "intent_scope"] });
  const columns = teamColumns({ users: users.data ?? [], busy: feedback.busy || users.isLoading || users.isError,
    add: (teamId, userId) => feedback.run(() => add.mutateAsync({ teamId, userId }), "成员已加入技能组。") });
  return <div className="af-page"><PageHeader title="技能组" subtitle="将业务范围和座席成员放在同一处管理。"
    actions={<RefreshButton query={query} />} /><ActionFeedback state={feedback} />
    <div className="af-work-stack"><TeamCreate /><WorkspacePanel title="座席技能组">
      <QueryFeedback query={users} /><FilterBar {...filter} placeholder="搜索技能组或意图范围" count={query.data ? filter.rows.length : undefined} />
      <DataTable query={query} dataSource={filter.rows} columns={columns} emptyTitle={filter.filtered ? "没有匹配的技能组" : "尚未创建技能组"}
        emptyDescription="创建技能组后，可选择账号添加成员。" />
    </WorkspacePanel></div>
  </div>;
}
