import { Collapse, Space, Tag } from "antd";
import { Link } from "react-router-dom";
import { DataTable, EmptyState, SettingsSection, WorkspacePanel } from "../../components/admin/workspace";
import type { FeaturesResponse } from "../../plugins/types";

export const PLUGIN_LABELS: Record<string, string> = {
  core: "系统核心", rag: "检索增强", agent: "智能客服", tools: "工具调用", ticket: "客服工单",
  handoff: "人工接管", knowledge: "知识闭环", ops: "运营配置", cost: "成本管理", sla: "服务时限",
  notify: "消息通知", sso: "单点登录", teams: "技能组", connectors: "业务连接器", launch: "上线卡片",
  analytics: "运营看板", mcp: "MCP 工具", widget: "嵌入客服", feishu: "飞书", wecom: "企业微信",
  dingtalk: "钉钉", qc: "对话质检", mall_core: "商城核心", mall_account: "商城账号",
  mall_catalog: "商品目录", mall_order: "订单与售后", mall_payment: "商城支付", mall_wallet: "商城钱包",
  mall_notify: "商城通知", mall_support: "商城客服", mall_referral: "邀请奖励", mall_admin: "商城管理",
};

export function PluginSummary({ data }: { data?: FeaturesResponse }) {
  const plugins = data?.plugins ?? [];
  const values = [
    { label: "运行配置", value: data?.profile },
    { label: "启用能力", value: data ? plugins.filter((plugin) => plugin.enabled).length : undefined },
    { label: "加载能力", value: data ? plugins.filter((plugin) => plugin.loaded).length : undefined },
    { label: "路由处理器", value: data?.route_handlers.length },
  ];
  return <dl className="af-plugin-summary">{values.map((item) => <div key={item.label}>
    <dt>{item.label}</dt><dd className={item.value == null ? "af-record-secondary" : undefined}>{item.value ?? "—"}</dd>
  </div>)}</dl>;
}

export function PluginConfiguration({ data }: { data?: FeaturesResponse }) {
  return <SettingsSection title="运行配置" description="能力在启动时装配。更改部署配置并重启服务后生效。">
    <dl className="af-plugin-config"><div><dt>可用配置</dt><dd><Space wrap>
      {data?.profiles?.map((profile) => <Tag key={profile}>{profile}{profile === data.profile ? " · 当前" : ""}</Tag>)}
      {!data?.profiles?.length && "—"}</Space></dd></div>
      <div><dt>增量能力</dt><dd>{data?.feature_deltas ? <code>{data.feature_deltas}</code> : "无增量配置"}</dd></div></dl>
    <Collapse ghost items={[{ key: "configure", label: "查看部署配置方法", children:
      <p className="af-work-help">使用 <code>ASKFLOW_PROFILE</code> 选择运行配置；
        通过 <code>ASKFLOW_FEATURES</code> 添加或移除能力，例如 <code>+sla,-mcp</code>。重启服务后，导航同步更新。</p> }]} />
  </SettingsSection>;
}

export function PluginExtensions({ data }: { data?: FeaturesResponse }) {
  const sections = [{ title: "对话路由", rows: data?.route_handlers ?? [] },
    { title: "后续处理", rows: data?.side_effects ?? [] }];
  return <div className="af-plugin-extensions">{sections.map((section) => <WorkspacePanel key={section.title}
    title={section.title} description={`${section.rows.length} 个已注册扩展点`}>
    {section.rows.length ? <ul className="af-plugin-extension-list">{section.rows.map((name) => <li key={name}><code>{name}</code></li>)}</ul> :
      <EmptyState title="暂无已注册扩展点" />}
  </WorkspacePanel>)}</div>;
}

export function PluginNavigation({ data }: { data?: FeaturesResponse }) {
  return <WorkspacePanel title="管理入口" description="已注册的管理页面与所属能力。">
    <DataTable rowKey={(row) => `${row.plugin_id}-${row.to}`} dataSource={data?.admin_nav ?? []}
      emptyTitle="暂无注册的管理入口" columns={[
        { title: "入口", dataIndex: "label", render: (label: string, row) => <Link to={row.to}>{label}</Link> },
        { title: "所属能力", dataIndex: "plugin_id", render: (id: string) => PLUGIN_LABELS[id] ?? id },
        { title: "路径", dataIndex: "to", render: (path: string) => <code>{path}</code> },
        { title: "顺序", dataIndex: "order", align: "right", className: "af-record-number" },
      ]} />
  </WorkspacePanel>;
}
