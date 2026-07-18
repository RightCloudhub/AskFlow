import { useEffect, useState } from "react";
import { Button, Card, Table, Tag } from "antd";
import { StopOutlined, CheckOutlined } from "@ant-design/icons";
import { api } from "../../api/client";
import { PageHeader, labelStatus } from "../../components/admin";

type U = {
  id: string;
  username: string;
  email: string;
  role: string;
  is_active: boolean;
};

export function UsersPage() {
  const [rows, setRows] = useState<U[]>([]);
  const [loading, setLoading] = useState(true);

  async function load() {
    setRows(await api<U[]>("/api/v1/admin/users"));
  }

  useEffect(() => {
    void load().finally(() => setLoading(false));
  }, []);

  async function toggle(u: U) {
    await api(`/api/v1/admin/users/${u.id}/active`, {
      method: "PATCH",
      body: JSON.stringify({ is_active: !u.is_active }),
    });
    await load();
  }

  return (
    <div className="af-page">
      <PageHeader
        eyebrow="系统治理"
        title="用户管理"
        subtitle="账号启用 / 禁用与角色一览"
      />
      <Card>
        <Table
          loading={loading}
          rowKey="id"
          dataSource={rows}
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
                a ? <Tag color="success">启用</Tag> : <Tag color="error">禁用</Tag>,
            },
            {
              title: "操作",
              key: "actions",
              render: (_: unknown, u: U) => (
                <Button
                  size="small"
                  danger={u.is_active}
                  type={u.is_active ? "default" : "primary"}
                  icon={u.is_active ? <StopOutlined /> : <CheckOutlined />}
                  onClick={() => void toggle(u)}
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
