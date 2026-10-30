import { useState } from "react";
import { Drawer } from "antd";
import type { Handoff } from "../../../api/types";
import { SessionFlow } from "./session-flow";

type SessionDetailProps = { open: boolean; session: Handoff | null; onClose: () => void };

export function SessionDetail({ open, session, onClose }: SessionDetailProps) {
  const [busy, setBusy] = useState(false);
  return <Drawer title="接管工作台" open={open} onClose={() => { if (!busy) onClose(); }}
    closable={!busy} keyboard={!busy} mask={{ closable: !busy }} size="min(560px, 100vw)" destroyOnHidden>
    {open && session && <SessionFlow key={session.id} session={session} onBusyChange={setBusy} onClose={onClose} />}
  </Drawer>;
}
