import type { ReactNode } from "react";
import {
  ApiOutlined,
  AuditOutlined,
  ClusterOutlined,
  DashboardOutlined,
  DatabaseOutlined,
  DollarOutlined,
  FileSearchOutlined,
  FileTextOutlined,
  FormOutlined,
  FundProjectionScreenOutlined,
  HistoryOutlined,
  PartitionOutlined,
  RocketOutlined,
  SafetyCertificateOutlined,
  TeamOutlined,
  ThunderboltOutlined,
  UserOutlined,
} from "@ant-design/icons";

const MAP: Record<string, ReactNode> = {
  dashboard: <DashboardOutlined />,
  qc: <SafetyCertificateOutlined />,
  cost: <DollarOutlined />,
  replay: <HistoryOutlined />,
  docs: <FileTextOutlined />,
  gap: <FileSearchOutlined />,
  draft: <FormOutlined />,
  intent: <PartitionOutlined />,
  prompt: <ThunderboltOutlined />,
  handoff: <ClusterOutlined />,
  ticket: <FundProjectionScreenOutlined />,
  team: <TeamOutlined />,
  sla: <SafetyCertificateOutlined />,
  users: <UserOutlined />,
  audit: <AuditOutlined />,
  connector: <ApiOutlined />,
  launch: <RocketOutlined />,
};

export function navIcon(name?: string): ReactNode {
  return MAP[name ?? ""] ?? <DatabaseOutlined />;
}
