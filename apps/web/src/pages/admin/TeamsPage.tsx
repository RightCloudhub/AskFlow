import { ConfigurationWorkspace } from "../../components/admin/record-workspace";
import { useState } from "react";
import { Button, Drawer } from "antd";
import type { ColumnsType } from "antd/es/table";
import { PageHeader } from "../../components/admin";
import { DataTable, FilterBar, RefreshButton, WorkspacePanel } from "../../components/admin/workspace";
import { useRecordFilter } from "../../components/admin/use-record-filter";
import { useTeams } from "../../hooks/use-ops";
import type { Team } from "../../api/types";

import { TeamCreate } from "./team-create";
import { TeamMemberFlow } from "./team-member-flow";

type MemberActions = { busy: boolean; select: (team: Team) => void };

function teamColumns(actions: MemberActions): ColumnsType<Team> {
  return [
    { title: "技能组", dataIndex: "name", render: (name, row) =>
      <div className="af-record-title"><strong>{name}</strong><small>{row.description || "未填写说明"}</small></div> },
    { title: "意图范围", dataIndex: "intent_scope", render: (value) => value || "未配置" },
    { title: "成员数", dataIndex: "member_count", align: "right", render: (value, row) => value ?? row.member_ids?.length ?? "—" },
    { title: "成员管理", key: "add", render: (_, row) => <Button size="small" disabled={actions.busy}
      onClick={() => actions.select(row)}>添加成员</Button> },
  ];
}

export function TeamsPage() {
  const query = useTeams();
  const [selected, setSelected] = useState<Team>();
  const [busy, setBusy] = useState(false);
  const current = query.data?.find((team) => team.id === selected?.id) ?? selected;
  const filter = useRecordFilter({ rows: query.data ?? [], fields: ["name", "intent_scope"] });
  const columns = teamColumns({ busy, select: setSelected });
  return <div className="af-page"><PageHeader title="技能组" subtitle="将业务范围和座席成员放在同一处管理。"
    actions={<RefreshButton query={query} />} />
    <ConfigurationWorkspace editor={<TeamCreate onAddMembers={setSelected} />}><WorkspacePanel title="座席技能组">
      <FilterBar {...filter} placeholder="搜索技能组或意图范围" count={query.data ? filter.rows.length : undefined} />
      <DataTable query={query} dataSource={filter.rows} columns={columns} emptyTitle={filter.filtered ? "没有匹配的技能组" : "尚未创建技能组"}
        emptyDescription="创建技能组后，可选择账号添加成员。" />
    </WorkspacePanel></ConfigurationWorkspace>
    <Drawer title={current ? `添加成员 · ${current.name}` : "添加成员"} open={Boolean(selected)}
      onClose={() => { if (!busy) setSelected(undefined); }} closable={!busy} keyboard={!busy} mask={{ closable: !busy }} destroyOnHidden>
      {current && <TeamMemberFlow key={current.id} team={current} onBusyChange={setBusy} />}
    </Drawer>
  </div>;
}
