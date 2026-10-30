import { Alert, Tabs, Tag } from "antd";
import { PageHeader } from "../../components/admin";
import { DataTable, FilterBar, RefreshButton, WorkspacePanel } from "../../components/admin/workspace";
import { useRecordFilter } from "../../components/admin/use-record-filter";
import { useFeaturesDiscovery } from "../../hooks/use-governance";
import { PLUGIN_LABELS, PluginConfiguration, PluginExtensions, PluginNavigation, PluginSummary } from "./plugin-parts";

const PLUGIN_STATES = [{ value: "all", label: "全部能力" }, { value: "true", label: "已启用" }, { value: "false", label: "未启用" }];

function PluginCatalog({ query }: { query: ReturnType<typeof useFeaturesDiscovery> }) {
  const plugins = (query.data?.plugins ?? []).map((plugin) => ({ ...plugin, label: PLUGIN_LABELS[plugin.id] ?? plugin.id }));
  const filter = useRecordFilter({ rows: plugins, fields: ["id", "label"], statusField: "enabled" });
  return <WorkspacePanel title="能力目录" description="查看已选择的能力、装配状态与依赖关系。">
    <FilterBar {...filter} count={query.data ? filter.rows.length : undefined} placeholder="搜索能力名称或标识" options={PLUGIN_STATES} />
    <DataTable query={query} dataSource={filter.rows} emptyTitle={filter.filtered ? "没有匹配的能力" : "暂无能力元数据"}
      emptyDescription={filter.filtered ? "试试其他关键词或清除筛选。" : "刷新以重新读取服务配置。"} columns={[
        { title: "能力", dataIndex: "label", render: (label, row) => <div className="af-record-title"><strong>{label}</strong><small>{row.id}</small></div> },
        { title: "依赖", dataIndex: "depends", render: (dependencies: string[]) => dependencies.length ? dependencies.map((id) => PLUGIN_LABELS[id] ?? id).join("、") : <span className="af-record-secondary">无依赖</span> },
        { title: "启用", dataIndex: "enabled", render: (enabled: boolean) => <Tag>{enabled ? "已启用" : "未启用"}</Tag> },
        { title: "加载", dataIndex: "loaded", render: (loaded: boolean, row) =>
          <Tag color={row.enabled && !loaded ? "warning" : undefined}>{loaded ? "已加载" : "未加载"}</Tag> },
      ]} />
  </WorkspacePanel>;
}

export function PluginsPage() {
  const query = useFeaturesDiscovery();
  const missing = (query.data?.plugins ?? []).filter((plugin) => plugin.enabled && !plugin.loaded);
  return <div className="af-page"><PageHeader title="插件与能力" subtitle="查看当前部署的能力、依赖与运行状态。"
    actions={<RefreshButton query={query} />} /><PluginSummary data={query.data} />
    {missing.length > 0 && <Alert type="warning" showIcon title={`${missing.length} 个能力已启用但未加载`}
      description={`${missing.map((plugin) => PLUGIN_LABELS[plugin.id] ?? plugin.id).join("、")}。请检查服务启动日志和依赖配置。`} />}
    <Tabs className="af-plugin-tabs" items={[
      { key: "catalog", label: "能力目录", children: <PluginCatalog query={query} /> },
      { key: "configuration", label: "部署配置", children: <PluginConfiguration data={query.data} /> },
      { key: "extensions", label: "扩展点", children: <PluginExtensions data={query.data} /> },
      { key: "navigation", label: "管理入口", children: <PluginNavigation data={query.data} /> },
    ]} />
  </div>;
}
