import { useCallback, useState } from "react";
import { Button, Typography } from "antd";
import { mall } from "./client";
import { Feedback, useLoad } from "./shared";

export function DemoCode({ challenge }: { challenge: string }) {
  const load = useCallback(() => mall<{ demo_mailbox: boolean }>("/features"), []);
  const query = useLoad(load);
  const [code, setCode] = useState("");
  const [error, setError] = useState("");
  const reveal = async () => {
    try {
      const result = await mall<{ code: string }>(`/account/verification/demo/${challenge}`);
      setCode(result.code);
    } catch { setError("演示验证码已失效，请重新发送。"); }
  };
  if (!query.data?.demo_mailbox) return null;
  return <><Typography.Text type="secondary">当前为本地演示，验证码不会外发。</Typography.Text>
    <Button onClick={() => { void reveal(); }}>查看演示验证码</Button>
    {code && <Typography.Text copyable>{code}</Typography.Text>}<Feedback error={error} /></>;
}
