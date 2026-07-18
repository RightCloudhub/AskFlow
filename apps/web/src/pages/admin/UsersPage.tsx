import { Button, Card, Table, Tag } from "antd";
import { CheckOutlined, StopOutlined } from "@ant-design/icons";
import { PageHeader, labelStatus } from "../../components/admin";
import { useToggleUser, useUsers } from "../../hooks/use-governance";
import type { User } from "../../api/types";

export function UsersPage() {
  const usersQ = useUsers();
  const toggle = useToggleUser();

  return (
    <div className="af-page">
      <PageHeader
        eyebrow="系统治理"
        title="用户管理"
        subtitle="账号启用 / 禁用与角色一览"
      />
      <Card>
        <Table
          loading={usersQ.isLoading}
          rowKey="id"
          dataSource={usersQ.data ?? []}
          pagination={{ pageSize: 10 }}
          columns={[
            { title: "用户名", dataIndex: "username" },
            { title: "邮箱", dataIndex: "email" },
            {
              title: "角色",
              dataIndex: "role",
              render: (r: string) => <Tag color="blue">{labelStatus(r)}</Tag>,
            },
            {
              title: "状态",
              dataIndex: "is_active",
              render: (a: boolean) =>
                a ? (
                  <Tag color="success">启用</Tag>
                ) : (
                  <Tag color="error">禁用</Tag>
                ),
            },
            {
              title: "操作",
              key: "actions",
              render: (_: unknown, u: User) => (
                <Button
                  size="small"
                  danger={Boolean(u.is_active)}
                  type={u.is_active ? "default" : "primary"}
                  icon={u.is_active ? <StopOutlined /> : <CheckOutlined />}
                  loading={toggle.isPending && toggle.variables?.id === u.id}
                  onClick={() => void toggle.mutateAsync(u)}
                >
                  {u.is_active ? "禁用" : "启用"}
                </Button>
              ),
            },
          ]}
          locale={{ emptyText: "暂无用户" }}
        />
      </Card>
    </div>
  );
}
