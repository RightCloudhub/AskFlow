import { Alert, Button } from "antd";
import { CustomerServiceOutlined } from "@ant-design/icons";

type HandoffBannerProps = {
  summary?: string;
  onGoAdmin?: () => void;
};

export function HandoffBanner({ summary, onGoAdmin }: HandoffBannerProps) {
  return (
    <Alert
      className="af-handoff-banner"
      type="info"
      showIcon
      icon={<CustomerServiceOutlined />}
      message="已申请人工客服"
      description={summary || "座席认领后将继续为您服务"}
      action={
        onGoAdmin ? (
          <Button size="small" type="link" onClick={onGoAdmin}>
            打开接管台
          </Button>
        ) : undefined
      }
    />
  );
}
