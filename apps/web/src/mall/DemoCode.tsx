import { useCallback, useState } from "react";
import { Button, Typography } from "antd";
import { mall } from "./client";
import { useLoad } from "./shared";
import { ActionFeedback, useActionFeedback } from "../components/common/action-feedback";

export function DemoCode({ challenge }: { challenge: string }) {
  const query = useLoad(useCallback(() => mall<{ demo_mailbox: boolean }>("/features"), []));
  const [code, setCode] = useState("");
  const feedback = useActionFeedback();
  if (!query.data?.demo_mailbox) return null;
  return <div className="af-demo-code"><p className="af-mall-note">当前为本地演示，验证码不会外发。</p>
    <Button loading={feedback.busy} onClick={() => void feedback.run(async () => {
      const result = await mall<{ code: string }>(`/account/verification/demo/${encodeURIComponent(challenge)}`);
      setCode(result.code);
    })}>查看演示验证码</Button>{code && <Typography.Text copyable>{code}</Typography.Text>}
    <ActionFeedback state={feedback} />
  </div>;
}
