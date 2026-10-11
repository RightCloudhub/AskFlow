import type { Handoff } from "../../api/types";

/** Actions a given agent can take on a row — one source of truth for the buttons. */
export function handoffActions(
  row: Pick<Handoff, "status" | "claimed_by">,
  currentUserId?: string | null,
): { claim: boolean; ret: boolean; claimedByOther: boolean } {
  const mine = Boolean(currentUserId) && row.claimed_by === currentUserId;
  return {
    claim: row.status === "queued",
    ret: row.status === "claimed" && mine,
    claimedByOther: row.status === "claimed" && !mine,
  };
}
