import { Button, Card, Popconfirm, Table, Tag } from "antd";
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
        subtitle="查看账号角色，启用或禁用账号"
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
                <Popconfirm
                  title={u.is_active ? "禁用该用户？" : "启用该用户？"}
                  description={
                    u.is_active
                      ? "禁用后该用户将无法登录。"
                      : "启用后该用户可重新登录。"
                  }
                  okText={u.is_active ? "禁用" : "启用"}
                  okButtonProps={{ danger: Boolean(u.is_active) }}
                  cancelText="取消"
                  onConfirm={() => toggle.mutateAsync(u)}
                >
                  <Button
                    size="small"
                    danger={Boolean(u.is_active)}
                    type={u.is_active ? "default" : "primary"}
                    icon={u.is_active ? <StopOutlined /> : <CheckOutlined />}
                    loading={toggle.isPending && toggle.variables?.id === u.id}
                  >
                    {u.is_active ? "禁用" : "启用"}
                  </Button>
                </Popconfirm>
              ),
            },
          ]}
          locale={{ emptyText: "暂无用户" }}
        />
      </Card>
    </div>
  );
}
