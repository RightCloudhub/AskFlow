import type { ReactNode } from "react";
import { Space, Typography } from "antd";

const { Title, Text } = Typography;

type PageHeaderProps = {
  title: string;
  subtitle?: string;
  /** Section label; the breadcrumb now carries it (kept for API compatibility). */
  eyebrow?: string;
  actions?: ReactNode;
};

export function PageHeader({ title, subtitle, actions }: PageHeaderProps) {
  return (
    <div className="af-page-header">
      <div className="af-page-header-text">
        <Title level={4} className="af-page-title">
          {title}
        </Title>
        {subtitle ? (
          <Text type="secondary" className="af-page-subtitle">
            {subtitle}
          </Text>
        ) : null}
      </div>
      {actions ? (
        <Space wrap className="af-page-actions">
          {actions}
        </Space>
      ) : null}
    </div>
  );
}
