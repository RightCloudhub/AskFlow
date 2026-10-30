// Run against admin-preview.mjs after apps/web has been built.
import assert from "node:assert/strict";
import { chromium } from "playwright";
import { fixtureResponse } from "./admin-fixtures.mjs";

const BASE = process.env.ADMIN_E2E_URL ?? "http://127.0.0.1:4180";
const WAIT_MS = 10000;
const DESKTOP = { width: 1440, height: 900 };
const PHONE = { width: 390, height: 844 };

async function identityPage(browser, identity) {
  const page = await browser.newPage({ viewport: DESKTOP });
  page.setDefaultTimeout(WAIT_MS);
  await page.addInitScript((value) => localStorage.setItem("askflow_token", "preview-" + value), identity);
  return page;
}

async function choose(page, label, option) {
  await page.getByRole("combobox", { name: label, exact: true }).click();
  await page.locator(".ant-select-dropdown:visible").getByText(option, { exact: true }).click();
}

async function expectHeading(page, name) {
  await page.getByRole("heading", { name, exact: true }).waitFor();
}

async function accessMatrix(browser) {
  const cases = [
    { identity: "customer", allowed: [], denied: "/admin/service/handoffs" },
    { identity: "agent", allowed: ["客服运营", "商城管理"], denied: "/admin/system/infra" },
    { identity: "catalog", allowed: ["商城管理"], denied: "/admin/system/mall/roles" },
    { identity: "finance", allowed: ["商城管理"], denied: "/admin/commerce/mall/catalog" },
    { identity: "rbac", allowed: ["系统管理"], denied: "/admin/system/mall/settings" },
  ];
  for (const row of cases) {
    const page = await identityPage(browser, row.identity);
    await page.goto(BASE + "/admin");
    if (!row.allowed.length) await expectHeading(page, "暂无访问权限");
    else {
      await expectHeading(page, row.allowed.length === 1 ? row.allowed[0] : "管理工作区");
      await page.getByRole("button", { name: "切换工作区", exact: true }).click();
      const menu = page.locator(".ant-dropdown:visible");
      for (const area of ["客服运营", "商城管理", "系统管理"]) {
        assert.equal(await menu.getByRole("menuitem", { name: area, exact: true }).count(), Number(row.allowed.includes(area)));
      }
    }
    await page.goto(BASE + row.denied);
    await expectHeading(page, "暂无访问权限");
    assert.equal(await page.getByRole("button", { name: "下一步", exact: true }).count(), 0);
    await page.close();
  }
}

async function sessionAndRevocation(browser) {
  const page = await identityPage(browser, "admin");
  await page.goto(BASE + "/admin/system/mall/roles");
  await expectHeading(page, "角色与权限");
  await page.evaluate(() => {
    localStorage.setItem("askflow_token", "preview-customer");
    dispatchEvent(new StorageEvent("storage", { key: "askflow_token" }));
  });
  await expectHeading(page, "暂无访问权限");
  assert.equal(await page.getByText("商城运营", { exact: true }).count(), 0);
  await page.close();
}

async function permissionRetry(browser) {
  const page = await identityPage(browser, "catalog");
  let failed = true;
  await page.route("**/api/v1/mall/admin/permissions", (route) => route.fulfill({
    status: failed ? 503 : 200, json: failed ? { detail: "Unavailable" } : fixtureResponse("/api/v1/mall/admin/permissions", "catalog"),
  }));
  await page.goto(BASE + "/admin/commerce/mall/catalog");
  await expectHeading(page, "访问权限暂不可用");
  failed = false;
  await page.getByRole("button", { name: "重新读取", exact: true }).click();
  await expectHeading(page, "商城商品");
  await page.close();
}

async function guidedProduct(browser) {
  const page = await identityPage(browser, "catalog");
  const commands = [];
  await page.route("**/api/v1/admin/mall/catalog/skus", (route) => {
    if (route.request().method() !== "POST") return route.continue();
    commands.push(route.request().postDataJSON());
    return route.fulfill({ status: 200, json: { id: "new-sku", version: 1 } });
  });
  await page.goto(BASE + "/admin/commerce/mall/catalog");
  await choose(page, "选择管理操作", "新增规格");
  await choose(page, "选择所属商品", "AskFlow 服务手册");
  await page.getByRole("button", { name: "下一步", exact: true }).click();
  assert.equal(await page.getByLabel("售价（元）", { exact: true }).isVisible(), false);
  await page.getByLabel("SKU 编码", { exact: true }).fill("AF-2026");
  await page.getByLabel("名称", { exact: true }).fill("标准版");
  await page.getByRole("button", { name: "下一步", exact: true }).click();
  await page.getByLabel("售价（元）", { exact: true }).fill("49.90");
  await page.getByLabel("原价（元）", { exact: true }).fill("59.90");
  await page.getByRole("button", { name: "上一步", exact: true }).click();
  assert.equal(await page.getByLabel("SKU 编码", { exact: true }).inputValue(), "AF-2026");
  await page.getByRole("button", { name: "下一步", exact: true }).click();
  await page.getByRole("button", { name: "下一步", exact: true }).click();
  await expectHeading(page, "核对后提交");
  assert.equal(commands.length, 0);
  await page.getByRole("button", { name: "新增规格", exact: true }).click();
  await page.getByText("操作已完成。", { exact: true }).waitFor();
  assert.deepEqual(commands, [{ spu_id: "product-af-1", code: "AF-2026", title: "标准版", sale_cents: 4990, original_cents: 5990 }]);
  await page.close();
}

async function confirmGrantRevocation(browser) {
  const page = await identityPage(browser, "rbac");
  let writes = 0;
  await page.route("**/api/v1/admin/mall/roles/grants/operator-1/role-ops", (route) => {
    assert.equal(route.request().method(), "DELETE");
    writes += 1;
    return route.fulfill({ status: 200, json: { status: "revoked" } });
  });
  await page.goto(BASE + "/admin/system/mall/roles");
  await choose(page, "选择管理操作", "撤销角色");
  await choose(page, "选择角色授权", "林晓 · 商城运营");
  await expectHeading(page, "核对后提交");
  assert.equal(writes, 0);
  await page.getByRole("button", { name: "撤销角色", exact: true }).click();
  await page.getByText("操作已完成。", { exact: true }).waitFor();
  assert.equal(writes, 1);
  await page.close();
}

async function responsiveAndLegacy(browser) {
  const page = await identityPage(browser, "admin");
  await page.goto(BASE + "/admin/prompts?source=saved#editor");
  await expectHeading(page, "提示词模板");
  assert.equal(new URL(page.url()).pathname, "/admin/system/prompts");
  assert.equal(new URL(page.url()).search, "?source=saved");
  assert.equal(new URL(page.url()).hash, "#editor");
  await page.setViewportSize(PHONE);
  for (const area of ["service", "commerce", "system"]) {
    await page.goto(BASE + "/admin/" + area);
    await page.getByRole("button", { name: "打开导航", exact: true }).waitFor();
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth > innerWidth);
    assert.equal(overflow, false, area + " overflows on a phone");
    await page.getByRole("button", { name: "打开导航", exact: true }).click();
    await page.getByRole("dialog").waitFor();
    await page.keyboard.press("Escape");
  }
  await page.close();
}

const browser = await chromium.launch();
try {
  for (const check of [accessMatrix, sessionAndRevocation, permissionRetry, guidedProduct,
    confirmGrantRevocation, responsiveAndLegacy]) {
    await check(browser);
    console.log(check.name + " passed");
  }
} finally { await browser.close(); }
