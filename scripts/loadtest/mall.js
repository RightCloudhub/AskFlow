import { browse, cart, checkout, flash, search, wallet } from "./mall-client.js";
export { browse, cart, checkout, flash, search, wallet };

const DEFAULT_DURATION_SECONDS = 60;
const FLASH_DURATION_SECONDS = 30;
const DEFAULT_VUS = 200;
const MAX_VUS_MULTIPLIER = 2;
const MAX_ERROR_RATE = 0.001;
const DURATION_SECONDS = positiveSetting("MALL_DURATION_SECONDS", DEFAULT_DURATION_SECONDS);
const PREALLOCATED = positiveSetting("MALL_VUS", DEFAULT_VUS);
const ARRIVAL = (exec, rate) => ({ executor: "constant-arrival-rate", exec, rate,
  timeUnit: "1s", duration: `${DURATION_SECONDS}s`, preAllocatedVUs: PREALLOCATED,
  maxVUs: PREALLOCATED * MAX_VUS_MULTIPLIER });
const SCENARIOS = {
  detail: ARRIVAL("browse", 3000), search: ARRIVAL("search", 800),
  order: ARRIVAL("checkout", 300), cart: ARRIVAL("cart", 300),
  wallet: ARRIVAL("wallet", 300), flash: { ...ARRIVAL("flash", 10000), duration: `${FLASH_DURATION_SECONDS}s` },
};
const selected = __ENV.MALL_SCENARIO || "detail";
if (!SCENARIOS[selected]) throw new Error("Unknown MALL_SCENARIO");
SCENARIOS[selected].rate = positiveSetting("MALL_RATE", SCENARIOS[selected].rate);
const operations = { detail: "detail", search: "search", order: "order", cart: "cart", wallet: "wallet-payment" };
const LATENCY = { detail: { operation: "detail", milliseconds: 50 }, search: { operation: "search", milliseconds: 150 },
  order: { operation: "order", milliseconds: 200 }, flash: { operation: "flash", milliseconds: 300 },
  wallet: { operation: "wallet-payment", milliseconds: 150 } };
const target = LATENCY[selected];
const latency = target ? {
  [`http_req_duration{name:${target.operation},status:200}`]: [`p(99)<${target.milliseconds}`],
} : {};
const throughput = selected === "flash" ? {} : {
  [`mall_completed_operations{operation:${operations[selected]}}`]: [
    `count>=${SCENARIOS[selected].rate * DURATION_SECONDS}`],
};

export const options = {
  scenarios: { [selected]: SCENARIOS[selected] },
  thresholds: {
    ...throughput,
    ...latency,
    mall_unexpected_errors: [`rate<${MAX_ERROR_RATE}`],
    dropped_iterations: ["count==0"],
  },
};

function positiveSetting(name, fallback) {
  const value = Number(__ENV[name] || fallback);
  if (!Number.isInteger(value) || value < 1) throw new Error(`${name} must be a positive integer`);
  return value;
}

export function handleSummary(data) {
  return { [`artifacts/mall-${selected}-summary.json`]: JSON.stringify(data, null, 2) };
}
