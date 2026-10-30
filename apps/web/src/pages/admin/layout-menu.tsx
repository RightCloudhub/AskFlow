import type { MenuProps } from "antd";
import { navIcon } from "../../components/admin";
import { groupNav } from "../../plugins/registry";
import { useAdminAccess } from "../../admin/use-admin-access";
import { currentWorkspace } from "../../admin/access-policy";

export function useAdminMenu(pathname: string) {
  const access = useAdminAccess();
  const requested = currentWorkspace(pathname);
  const workspace = access.workspaces.find((area) => area.id === requested?.id);
  const sections = groupNav(access.items.filter((item) => workspace
    ? item.to.startsWith(`/admin/${workspace.id}/`) : false));
  const items: MenuProps["items"] = sections.map(({ group, items: children }) => ({
    key: group.id,
    label: group.label,
    children: children.map((item) => ({ key: item.to, icon: navIcon(item.icon),
      label: item.label, title: item.hint })),
  }));
  if (workspace) items.unshift({ key: `/admin/${workspace.id}`, label: `${workspace.title}首页`, icon: navIcon("dashboard") });
  else items.push(...access.workspaces.map((area) => ({ key: `/admin/${area.id}`, label: area.title, icon: navIcon("dashboard") })));
  const selected = pathname.replace(/\/$/, "");
  const group = sections.find((section) => section.items.some((item) => item.to === selected));
  const item = group?.items.find((candidate) => candidate.to === selected);
  const crumb = group && item ? { group: group.group.label, page: item.label } : null;
  return { items, selected, crumb, workspace, sections: groupNav(access.items), activeGroup: group?.group.id };
}
