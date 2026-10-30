import assert from "node:assert/strict";
import { randomUUID } from "node:crypto";
import { readFile } from "node:fs/promises";
import { chromium, request } from "playwright";

const baseURL = process.env.MALL_E2E_URL ?? "http://127.0.0.1:8000";
const seedPath = process.env.MALL_SEED_FILE ?? "../../artifacts/mall-seed.json";
const WAIT_MS = 15000;
const REGISTERED = 202;
const prefix = "/api/v1/mall";
const fixture = JSON.parse(await readFile(seedPath, "utf8"));

async function account(api) {
  const username = "browser_" + randomUUID().replaceAll("-", "");
  const password = "Browser1!" + randomUUID();
  const sent = await api.post(prefix + "/account/verification/send", {
    data: { target: username + "@example.com", channel: "email", purpose: "register" },
  });
  assert.ok(sent.ok());
  const { challenge_id } = await sent.json();
  const mailbox = await api.get(prefix + "/account/verification/demo/" + challenge_id);
  assert.ok(mailbox.ok(), "Use an isolated development deployment with its demo mailbox enabled");
  const { code } = await mailbox.json();
  const verified = await api.post(prefix + "/account/verification/verify", { data: { challenge_id, code } });
  assert.ok(verified.ok());
  const registered = await api.post(prefix + "/account/register", {
    headers: { "Idempotency-Key": randomUUID() },
    data: { username, password, ...await verified.json() },
  });
  assert.equal(registered.status(), REGISTERED);
  return { username, password };
}

async function purchase(page, identity) {
  await page.goto(baseURL + "/shop/account");
  await page.getByLabel("用户名 / 邮箱 / 手机号", { exact: true }).fill(identity.username);
  await page.getByLabel("密码", { exact: true }).fill(identity.password);
  await page.getByRole("button", { name: "登录", exact: true }).click();
  await page.waitForURL("**/shop", { timeout: WAIT_MS });
  await page.goto(baseURL + "/shop/products/" + fixture.spu_id);
  await page.getByRole("button", { name: "加入购物车", exact: true }).click();
  await page.getByText("已加入购物车", { exact: true }).waitFor();
  await page.getByRole("link", { name: "前往购物车" }).click();
  await page.getByRole("button", { name: "核对金额" }).click();
  await page.getByRole("button", { name: "确认下单" }).click();
  await page.waitForURL("**/shop/orders/*", { timeout: WAIT_MS });
  await page.getByRole("button", { name: "支付", exact: true }).click();
  await page.getByRole("button", { name: "模拟支付成功", exact: true }).click();
  await page.getByText("PAID", { exact: true }).waitFor({ timeout: WAIT_MS });
}

const api = await request.newContext({ baseURL });
const browser = await chromium.launch();
try {
  const identity = await account(api);
  const page = await browser.newPage();
  await purchase(page, identity);
  await page.goto(baseURL + "/admin/mall/wallet");
  await page.getByRole("heading", { name: "暂无访问权限", exact: true }).waitFor();
  console.log("Mall browser purchase and financial permission smoke passed");
} finally {
  await browser.close();
  await api.dispose();
}
