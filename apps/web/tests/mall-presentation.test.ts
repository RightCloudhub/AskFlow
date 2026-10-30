import assert from "node:assert/strict";
import test from "node:test";
import { readableError } from "../src/components/common/error-text.ts";
import { majorToMinor, submissionValues } from "../src/mall/money-values.ts";

test("visible decimal amounts become integer API cents without changing other fields", () => {
  const values = { amount_cents: 19.99, quantity: 3, password: " keep spaces " };
  const result = submissionValues(values, [{ name: "amount_cents", kind: "money" }, { name: "quantity", kind: "number" }]);
  assert.deepEqual(result, { amount_cents: 1999, quantity: 3, password: " keep spaces " });
  assert.equal(values.amount_cents, 19.99);
  assert.equal(majorToMinor(0.29), 29);
  assert.equal(majorToMinor(0), 0);
  assert.deepEqual(submissionValues({}, [{ name: "amount_cents", kind: "money" }]), {});
});

test("nonfinite and unsafe monetary values never reach the API", () => {
  assert.throws(() => majorToMinor(Number.NaN), /金额无效/);
  assert.throws(() => majorToMinor(Number.POSITIVE_INFINITY), /金额无效/);
  assert.throws(() => majorToMinor(Number.MAX_SAFE_INTEGER), /金额无效/);
});

test("business errors and validation responses become actionable Chinese messages", () => {
  assert.match(readableError({ code: "wallet_insufficient", message: "wallet insufficient" }), /余额不足/);
  assert.match(readableError(new Error("verification invalid")), /重新发送/);
  assert.match(readableError(new Error('{"detail":"version_conflict"}')), /刷新/);
  assert.match(readableError({ detail: [{ loc: ["body", "target"], msg: "Field required" }] }), /字段提示/);
  assert.match(readableError(new TypeError("Failed to fetch")), /检查网络/);
  assert.equal(readableError(new Error("请先完成当前审核。")), "请先完成当前审核。");
  assert.equal(readableError(null), "操作未完成，请稍后重试。");
});
