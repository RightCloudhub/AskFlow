import http from "k6/http";
import { check } from "k6";
import { Counter, Rate } from "k6/metrics";

export const failures = new Rate("mall_unexpected_errors");
export const completed = new Counter("mall_completed_operations");
export const base = __ENV.MALL_BASE_URL || "http://127.0.0.1:8000";
export const seed = JSON.parse(open(__ENV.MALL_SEED || "../../artifacts/mall-seed.json"));
const EXPECTED = [200, 201, 202, 409, 429];

export function account() {
  return seed.users[(__VU - 1) % seed.users.length];
}

export function call(method, path, body, name) {
  const user = account();
  const params = { headers: { "Content-Type": "application/json", Authorization: `Bearer ${user.access_token}`,
    "Idempotency-Key": `${__VU}:${__ITER}:${name}:${Date.now()}` }, tags: { name },
    responseCallback: http.expectedStatuses(...EXPECTED) };
  const response = http.request(method, base + path, body === null ? null : JSON.stringify(body), params);
  const data = response.headers["Content-Type"]?.includes("json") ? response.json() : {};
  const expectedConflict = response.status === 409 && ["inventory_insufficient", "flash_sale_closed"].includes(data.code);
  const success = response.status < 400 || response.status === 429 || expectedConflict;
  failures.add(!success, { scenario: name });
  if (response.status >= 200 && response.status < 300) completed.add(1, { operation: name });
  check(response, { "expected business outcome": () => success });
  return response;
}

export function browse() {
  call("GET", `/api/v1/mall/catalog/products/${seed.spu_id}`, null, "detail");
}

export function search() {
  call("GET", "/api/v1/mall/catalog/search?q=Load", null, "search");
}

export function checkout() {
  purchase("mock");
}

function purchase(method) {
  const body = { items: [{ sku_id: seed.sku_id, qty: 1 }] };
  const quote = call("POST", "/api/v1/mall/order/checkout", body, "quote");
  if (quote.status !== 200) return;
  const order = call("POST", "/api/v1/mall/order/orders", {
    ...body, checkout_token: quote.json("checkout_token"),
  }, "order");
  if (order.status !== 200) return;
  const payment = call("POST", "/api/v1/mall/payment", { order_id: order.json("id"), method }, method === "wallet" ? "wallet-payment" : "payment");
  if (payment.status === 200 && method === "mock") call("POST", `/api/v1/mall/payment/${payment.json("id")}/mock`, {}, "callback");
}

export function cart() {
  call("PUT", "/api/v1/mall/order/cart/items", { sku_id: seed.sku_id, qty: 1 }, "cart");
}

export function flash() {
  call("POST", `/api/v1/mall/inventory/flash-sales/${seed.sale_id}`, { sku_id: seed.sku_id }, "flash");
}

export function wallet() {
  purchase("wallet");
}
