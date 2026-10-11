/** Ops-feedback helper checks (P1/P4/P5): run with `npm run test:ops`. */
import { formatWaiting, gapReason, intentLabel, ticketTypeLabel } from "./labels.ts";
import { handoffActions } from "../handoff/actions.ts";

// Tiny local assert: the web app has no @types/node, so node:assert would fail tsc.
const assert = {
  equal(actual: unknown, expected: unknown, msg?: string) {
    if (actual !== expected) throw new Error(`${msg ?? ""} expected ${String(expected)}, got ${String(actual)}`);
  },
  notEqual(actual: unknown, expected: unknown, msg?: string) {
    if (actual === expected) throw new Error(`${msg ?? ""} expected not ${String(expected)}`);
  },
  deepEqual(actual: unknown, expected: unknown) {
    const a = JSON.stringify(actual);
    const e = JSON.stringify(expected);
    if (a !== e) throw new Error(`expected ${e}, got ${a}`);
  },
};

const NOW = Date.parse("2026-10-11T13:30:00Z");

// P1: gap reasons are Chinese, legacy rows say so
assert.equal(gapReason("zero_hit").label, "无命中");
assert.equal(gapReason("weak_evidence").label, "证据不足");
assert.equal(gapReason("skipped").label, "未记录原因");
assert.equal(gapReason(null).label, "未记录原因");

// P4: naive server timestamps are UTC, not browser-local
assert.equal(formatWaiting("2026-10-11T13:07:47.960813", NOW), "22 分钟");
assert.equal(formatWaiting("2026-10-11T13:07:47Z", NOW), "22 分钟");
assert.equal(formatWaiting("2026-10-11T21:07:47+08:00", NOW), "22 分钟");
assert.equal(formatWaiting("2026-10-11T10:00:00", NOW), "3 小时 30 分");
assert.equal(formatWaiting("2026-10-09T10:00:00", NOW), "2 天 3 小时");
assert.equal(formatWaiting(null, NOW), "—");

// P4: buttons follow status and ownership
assert.deepEqual(handoffActions({ status: "queued", claimed_by: null }, "me"), {
  claim: true,
  ret: false,
  claimedByOther: false,
});
assert.deepEqual(handoffActions({ status: "claimed", claimed_by: "me" }, "me"), {
  claim: false,
  ret: true,
  claimedByOther: false,
});
assert.deepEqual(handoffActions({ status: "claimed", claimed_by: "other" }, "me"), {
  claim: false,
  ret: false,
  claimedByOther: true,
});
assert.deepEqual(handoffActions({ status: "claimed", claimed_by: "other" }, null), {
  claim: false,
  ret: false,
  claimedByOther: true,
});

// P5: business ticket types and intents are Chinese
for (const t of ["after_sales", "invoice", "account", "logistics", "refund", "complaint"]) {
  assert.notEqual(ticketTypeLabel(t), t, t);
}
assert.equal(intentLabel("handoff"), "转人工");

console.log("ops labels ok");
