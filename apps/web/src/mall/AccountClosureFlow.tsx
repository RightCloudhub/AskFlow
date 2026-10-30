import { useEffect, useState } from "react";
import { Alert, Button, Checkbox } from "antd";
import { Link } from "react-router-dom";
import { setToken } from "../api/client";
import { FlowFrame } from "../components/common/FlowFrame";
import { ActionFeedback, useActionFeedback } from "../components/common/action-feedback";
import { useFeatures } from "../plugins/features";
import { StepUp } from "./StepUp";
import { write } from "./client";
import { hasMallError } from "./request-error";

const TITLES = ["了解注销影响", "确认身份", "确认注销"];
const CONFIRM_STEP = TITLES.length - 1;
type ClosureProps = { active: boolean; onBusyChange: (busy: boolean) => void };

function useAccountClosure({ onBusyChange }: ClosureProps) {
  const [current, setCurrent] = useState(0);
  const [token, setProof] = useState("");
  const [acknowledged, setAcknowledged] = useState(false);
  const [identityBusy, setIdentityBusy] = useState(false);
  const [identityRevision, setIdentityRevision] = useState(0);
  const [complete, setComplete] = useState(false);
  const feedback = useActionFeedback();
  const busy = identityBusy || feedback.busy;
  useEffect(() => { onBusyChange(busy); }, [busy, onBusyChange]);
  function back(index: number) {
    if (busy || complete || index < 0 || index >= current) return;
    setAcknowledged(false); setCurrent(index); feedback.clear();
  }
  async function close() {
    if (!token || !acknowledged || busy || complete || current !== CONFIRM_STEP) return;
    await feedback.run(async () => {
      try { await write("/account/close", { step_up_token: token }); }
      catch (error) {
        if (hasMallError(error, "step_up_required")) {
          setProof(""); setAcknowledged(false); setCurrent(1); setIdentityRevision((value) => value + 1);
        }
        throw error;
      }
      setComplete(true);
      setToken(null);
      window.location.assign("/shop/account");
    });
  }
  return { current, setCurrent, token, setProof, acknowledged, setAcknowledged, setIdentityBusy,
    identityRevision, complete, feedback, busy, back, close };
}

function ClosureConsequences() {
  const { enabled } = useFeatures();
  return <div className="af-flow-success">
    <div className="af-form-review"><dl>
      <div><dt>注销条件</dt><dd>钱包可用余额和冻结资金均须结清，订单和支付须处理完成。</dd></div>
      <div><dt>账号与登录</dt><dd>账号将停用，所有设备退出登录，个人资料将脱敏。</dd></div>
      <div><dt>数据保留</dt><dd>财务记录按规定保留。如需备份，请先在上方导出个人数据。</dd></div>
    </dl></div>
    <p className="af-mall-note">提交注销时，系统会检查是否满足条件。</p>
    <div className="af-work-actions">
      {enabled("mall_order") && <Link to="/shop/orders">查看未完成订单</Link>}
      {enabled("mall_wallet") && <Link to="/shop/wallet">查看钱包资金</Link>}
    </div>
  </div>;
}

function ClosureNavigation({ state }: { state: ReturnType<typeof useAccountClosure> }) {
  const canContinue = !state.busy && (state.current === 0 || Boolean(state.token));
  const canClose = Boolean(state.token) && state.acknowledged && !state.complete;
  return <div className="af-form-flow-actions">
    {state.current > 0 && <Button disabled={state.busy || state.complete} onClick={() => state.back(state.current - 1)}>上一步</Button>}
    {state.current === CONFIRM_STEP
      ? <Button type="primary" danger loading={state.busy} disabled={!canClose} onClick={() => void state.close()}>确认注销并退出</Button>
      : <Button type="primary" disabled={!canContinue} onClick={() => state.setCurrent(state.current + 1)}>
        {state.current === 0 ? "继续验证身份" : "下一步"}</Button>}
  </div>;
}

export function AccountClosureFlow(props: ClosureProps) {
  const state = useAccountClosure(props);
  return <FlowFrame titles={TITLES} current={state.current} active={props.active}
    onBack={state.back} busy={state.busy} backDisabled={state.complete} focusOnMount>
    {state.current === 0 && <ClosureConsequences />}
    <div hidden={state.current !== 1}>
      <StepUp key={state.identityRevision} purpose="account_close" onToken={state.setProof} onBusyChange={state.setIdentityBusy} />
    </div>
    {state.current === CONFIRM_STEP && <div className="af-flow-success">
      <Alert type="warning" showIcon title="确认注销当前账号？" description="注销后无法使用此账号登录，个人资料将脱敏，财务记录按规定保留。" />
      <Checkbox checked={state.acknowledged} disabled={state.busy || state.complete}
        onChange={(event) => state.setAcknowledged(event.target.checked)}>我已了解注销影响，确认注销此账号。</Checkbox>
    </div>}
    <ActionFeedback state={state.feedback} />
    <ClosureNavigation state={state} />
  </FlowFrame>;
}
