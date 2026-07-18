import { useState } from "react";
import { Alert, Button, Card, Input, Select, Space, Table, Tag } from "antd";
import { PlusOutlined } from "@ant-design/icons";
import { PageHeader } from "../../components/admin";
import {
  useAddTeamMember,
  useCreateTeam,
  useTeams,
} from "../../hooks/use-ops";
import { useUsers } from "../../hooks/use-governance";
import type { Team } from "../../api/types";

export function TeamsPage() {
  const [name, setName] = useState("");
  const [scope, setScope] = useState("");
  const [msg, setMsg] = useState("");
  const teamsQ = useTeams();
  const usersQ = useUsers();
  const create = useCreateTeam();
  const addMember = useAddTeamMember();

  async function onCreate() {
    if (!name.trim()) return;
    await create.mutateAsync({ name: name.trim(), scope: scope.trim() });
    setName("");
    setScope("");
    setMsg("已创建技能组");
  }

  async function onAdd(teamId: string, userId: string) {
    if (!userId) return;
    await addMember.mutateAsync({ teamId, userId });
    setMsg("已添加成员");
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
          <Button
            type="primary"
            icon={<PlusOutlined />}
            loading={create.isPending}
            onClick={() => void onCreate()}
          >
            创建
          </Button>
        </Space>
      </Card>

      <Card title="技能组列表">
        <Table
          loading={teamsQ.isLoading || usersQ.isLoading}
          rowKey="id"
          dataSource={teamsQ.data ?? []}
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
                  options={(usersQ.data ?? []).map((u) => ({
                    value: u.id,
                    label: `${u.username} (${u.role})`,
                  }))}
                  onChange={(uid) => void onAdd(t.id, uid)}
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
