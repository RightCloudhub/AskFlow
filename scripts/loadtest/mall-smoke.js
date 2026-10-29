import { browse, cart, checkout, search } from "./mall-client.js";

export const options = { vus: 2, iterations: 10,
  thresholds: { mall_unexpected_errors: ["rate<0.001"], checks: ["rate==1"] } };

export default function () {
  browse(); search(); cart(); checkout();
}

export function handleSummary(data) {
  return { "artifacts/mall-smoke-summary.json": JSON.stringify(data, null, 2) };
}
