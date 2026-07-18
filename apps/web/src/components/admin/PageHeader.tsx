import { Flex, Space, Typography } from "antd";

const { Title, Text } = Typography;

type PageHeaderProps = {
  title: string;
  subtitle?: string;
  eyebrow?: string;
  actions?: React.ReactNode;
};

export function PageHeader({ title, subtitle, eyebrow, actions }: PageHeaderProps) {
  return (
    <Flex
      justify="space-between"
      align="flex-start"
      gap={16}
      wrap="wrap"
      className="af-page-header"
    >
      <div>
        {eyebrow ? (
          <Text type="secondary" style={{ fontSize: 12, letterSpacing: "0.06em" }}>
            {eyebrow.toUpperCase()}
          </Text>
        ) : null}
        <Title level={3} style={{ margin: "4px 0 0" }}>
          {title}
        </Title>
        {subtitle ? (
          <Text type="secondary" style={{ display: "block", marginTop: 4 }}>
            {subtitle}
          </Text>
        ) : null}
      </div>
      {actions ? <Space wrap>{actions}</Space> : null}
    </Flex>
  );
}
