import { Button } from "antd";
import { UserSwitchOutlined } from "@ant-design/icons";

type ClaimButtonProps = {
  loading?: boolean;
  onClick: () => void;
  label?: string;
};

export function ClaimButton({
  loading,
  onClick,
  label = "认领",
}: ClaimButtonProps) {
  return (
    <Button
      type="primary"
      size="small"
      icon={<UserSwitchOutlined />}
      loading={loading}
      onClick={onClick}
    >
      {label}
    </Button>
  );
}
