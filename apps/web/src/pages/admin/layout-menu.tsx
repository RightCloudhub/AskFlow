import { useMemo } from "react";
import type { MenuProps } from "antd";
import { navIcon } from "../../components/admin";
import { filterNav, groupNav } from "../../plugins/registry";
import { useMallPermissions } from "../../mall/permissions";
import { mallMenuAllowed } from "../../mall/menu";

export function useAdminMenu(features: Set<string>, pathname: string) {
  const { permissions } = useMallPermissions();
  const sections = useMemo(() => groupNav(filterNav(features).filter((item) =>
    mallMenuAllowed(item.to, permissions))), [features, permissions]);
  const items: MenuProps["items"] = sections.map(({ group, items: children }) => ({
    key: group.id,
    label: group.label,
    children: children.map((item) => ({ key: item.to, icon: navIcon(item.icon),
      label: item.label, title: item.hint })),
  }));
  const selected = pathname.replace(/\/$/, "");
  const group = sections.find((section) => section.items.some((item) => item.to === selected));
  const item = group?.items.find((candidate) => candidate.to === selected);
  const crumb = group && item ? { group: group.group.label, page: item.label } : null;
  return { items, selected, crumb, sections, activeGroup: group?.group.id };
}
