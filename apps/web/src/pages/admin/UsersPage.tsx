import { RecordWorkspace } from "../../components/admin/record-workspace";
import { Button, Popconfirm } from "antd";
import type { ColumnsType } from "antd/es/table";
import { PageHeader, StatusBadge, labelStatus } from "../../components/admin";
import { DataTable, FilterBar, RefreshButton, WorkspacePanel } from "../../components/admin/workspace";
import { useRecordFilter } from "../../components/admin/use-record-filter";
import { ActionFeedback, useActionFeedback } from "../../components/common/action-feedback";
import { useToggleUser, useUsers } from "../../hooks/use-governance";
import type { User } from "../../api/types";

type UserActions = { busy: boolean; toggle: (user: User) => Promise<unknown> };

function userColumns(actions: UserActions): ColumnsType<User> {
  return [
    { title: "账号", dataIndex: "username", render: (name, row) => <div className="af-record-title">
      <strong>{name}</strong><small>{row.email || "未填写邮箱"}</small></div> },
    { title: "角色", dataIndex: "role", render: (value) => labelStatus(value) },
    { title: "登录状态", dataIndex: "is_active", render: (value) =>
      <StatusBadge value={value == null ? undefined : value ? "enabled" : "disabled"} /> },
    { title: "操作", key: "action", render: (_, user) => <Popconfirm
      title={user.is_active ? "禁用 " + user.username + "？" : "启用 " + user.username + "？"}
      description={user.is_active ? "禁用后该账号将无法登录，已有业务记录会保留。" : "启用后该账号可以重新登录。"}
      okText={user.is_active ? "确认禁用" : "确认启用"} cancelText="取消"
      okButtonProps={{ danger: Boolean(user.is_active) }} onConfirm={() => actions.toggle(user)}>
      <Button size="small" danger={Boolean(user.is_active)} disabled={actions.busy || user.is_active == null}>
        {user.is_active ? "禁用账号" : "启用账号"}</Button>
    </Popconfirm> },
  ];
}

export function UsersPage() {
  const query = useUsers();
  const toggle = useToggleUser();
  const feedback = useActionFeedback();
  const filter = useRecordFilter({ rows: query.data ?? [], fields: ["username", "email"], statusField: "role" });
  const columns = userColumns({ busy: feedback.busy, toggle: (user) => feedback.run(
    () => toggle.mutateAsync(user), user.username + (user.is_active ? " 已禁用。" : " 已启用。")) });
  return <div className="af-page"><PageHeader title="用户管理" subtitle="查看账号角色和登录状态，保留每次启停操作的业务记录。"
    actions={<RefreshButton query={query} />} /><ActionFeedback state={feedback} />
    <RecordWorkspace rows={query.data} field="role" states={[{ value: "admin", label: "管理员" }, { value: "agent", label: "座席" }, { value: "user", label: "用户" }]}
      selected={filter.status} onSelect={filter.onStatus}>
      <WorkspacePanel title="用户账号">
      <FilterBar {...filter} placeholder="搜索用户名或邮箱" count={query.data ? filter.rows.length : undefined}
        options={[{ value: "all", label: "全部角色" }, { value: "admin", label: "管理员" },
          { value: "agent", label: "座席" }, { value: "user", label: "用户" }]} />
      <DataTable query={query} dataSource={filter.rows} columns={columns} emptyTitle={filter.filtered ? "没有匹配的用户" : "暂无用户账号"}
        emptyDescription={filter.filtered ? "尝试其他用户名、邮箱或角色。" : "账号创建后会出现在这里。"} />
    </WorkspacePanel>
    </RecordWorkspace>
  </div>;
}
