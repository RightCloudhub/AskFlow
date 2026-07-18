import { useEffect, useState } from "react";
import { Alert, Button, Card, Input, Select, Space, Table, Tag } from "antd";
import { PlusOutlined } from "@ant-design/icons";
import { api } from "../../api/client";
import { PageHeader } from "../../components/admin";

type Team = {
  id: string;
  name: string;
  description: string;
  intent_scope: string;
  member_ids?: string[];
  member_count?: number;
};

type UserRow = { id: string; username: string; email: string; role: string };

export function TeamsPage() {
  const [rows, setRows] = useState<Team[]>([]);
  const [users, setUsers] = useState<UserRow[]>([]);
  const [name, setName] = useState("");
  const [scope, setScope] = useState("");
  const [msg, setMsg] = useState("");
  const [loading, setLoading] = useState(true);

  async function load() {
    const [teams, us] = await Promise.all([
      api<Team[]>("/api/v1/admin/teams"),
      api<UserRow[]>("/api/v1/admin/users"),
    ]);
    setRows(teams);
    setUsers(us);
  }

  useEffect(() => {
    void load().finally(() => setLoading(false));
  }, []);

  async function createTeam() {
    if (!name.trim()) return;
    await api("/api/v1/admin/teams", {
      method: "POST",
      body: JSON.stringify({
        name: name.trim(),
        intent_scope: scope.trim(),
        description: "",
      }),
    });
    setName("");
    setScope("");
    setMsg("已创建技能组");
    await load();
  }

  async function addMember(teamId: string, userId: string) {
    if (!userId) return;
    await api(`/api/v1/admin/teams/${teamId}/members`, {
      method: "POST",
      body: JSON.stringify({ user_id: userId }),
    });
    setMsg("已添加成员");
    await load();
  }

  return (
    <div className="af-page">
      <PageHeader
        eyebrow="客服运营"
        title="技能组"
        subtitle="座席分组与意图范围配置"
      />
      {msg ? (
        <Alert type="success" showIcon message={msg} style={{ marginBottom: 16 }} />
      ) : null}

      <Card title="新建技能组" style={{ marginBottom: 16 }}>
        <Space wrap>
          <Input
            placeholder="名称"
            value={name}
            onChange={(e) => setName(e.target.value)}
            style={{ width: 180 }}
          />
          <Input
            placeholder="意图范围（逗号分隔）"
            value={scope}
            onChange={(e) => setScope(e.target.value)}
            style={{ width: 240 }}
          />
          <Button type="primary" icon={<PlusOutlined />} onClick={() => void createTeam()}>
            创建
          </Button>
        </Space>
      </Card>

      <Card title="技能组列表">
        <Table
          loading={loading}
          rowKey="id"
          dataSource={rows}
          pagination={false}
          columns={[
            { title: "名称", dataIndex: "name" },
            {
              title: "意图范围",
              dataIndex: "intent_scope",
              render: (s: string) => s || "—",
            },
            {
              title: "成员数",
              dataIndex: "member_count",
              width: 100,
              render: (n: number) => <Tag color="blue">{n ?? 0}</Tag>,
            },
            {
              title: "添加成员",
              key: "add",
              width: 220,
              render: (_: unknown, t: Team) => (
                <Select
                  placeholder="选择用户"
                  style={{ width: 200 }}
                  options={users.map((u) => ({
                    value: u.id,
                    label: `${u.username} (${u.role})`,
                  }))}
                  onChange={(uid) => void addMember(t.id, uid)}
                  value={null as unknown as string}
                />
              ),
            },
          ]}
          locale={{ emptyText: "暂无技能组" }}
        />
      </Card>
    </div>
  );
}
