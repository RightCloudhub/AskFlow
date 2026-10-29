import { Suspense, lazy } from "react";
import { Layout, Menu, Spin, Typography } from "antd";
import { Link, Navigate, Route, Routes, useLocation } from "react-router-dom";
import { getToken } from "../api/client";
import { useFeatures } from "../plugins/features";

const Catalog = lazy(() => import("./Catalog").then((m) => ({ default: m.Catalog })));
const Product = lazy(() => import("./Catalog").then((m) => ({ default: m.ProductDetail })));
const Cart = lazy(() => import("./Cart").then((m) => ({ default: m.Cart })));
const Orders = lazy(() => import("./Orders").then((m) => ({ default: m.Orders })));
const Order = lazy(() => import("./Orders").then((m) => ({ default: m.OrderDetail })));
const Account = lazy(() => import("./Account").then((m) => ({ default: m.Account })));
const Wallet = lazy(() => import("./Wallet").then((m) => ({ default: m.Wallet })));
const Referral = lazy(() => import("./Referral").then((m) => ({ default: m.Referral })));
const Messages = lazy(() => import("./Messages").then((m) => ({ default: m.Messages })));
const AfterSales = lazy(() => import("./AfterSales").then((m) => ({ default: m.AfterSales })));
const PaymentResult = lazy(() => import("./AfterSales").then((m) => ({ default: m.PaymentResult })));
const CONTENT_PADDING = 24;
const CONTENT_WIDTH = 1200;

const PAGES = [
  { path: "", plugin: "mall_catalog", title: "商品", page: <Catalog />, public: true },
  { path: "products/:id", plugin: "mall_catalog", page: <Product />, public: true },
  { path: "cart", plugin: "mall_order", title: "购物车", page: <Cart /> },
  { path: "checkout", plugin: "mall_order", page: <Cart /> },
  { path: "orders", plugin: "mall_order", title: "订单", page: <Orders /> },
  { path: "orders/:id", plugin: "mall_order", page: <Order /> },
  { path: "refunds", plugin: "mall_order", title: "售后", page: <AfterSales /> },
  { path: "payment-result", plugin: "mall_payment", page: <PaymentResult /> },
  { path: "wallet", plugin: "mall_wallet", title: "钱包", page: <Wallet /> },
  { path: "referral", plugin: "mall_referral", title: "邀请", page: <Referral /> },
  { path: "messages", plugin: "mall_notify", also: "mall_support", title: "消息与客服", page: <Messages /> },
  { path: "account", plugin: "mall_account", title: "账号", page: <Account />, public: true },
];

export function Shop() {
  const { enabled } = useFeatures();
  const location = useLocation();
  const pages = PAGES.filter((page) => enabled(page.plugin) || (page.also && enabled(page.also)));
  return <Layout style={{ minHeight: "100vh" }}>
    <Layout.Header style={{ background: "white", height: "auto" }}>
      <Link to="/shop"><Typography.Title level={3}>AskFlow 商城</Typography.Title></Link>
      <Menu mode="horizontal" selectedKeys={[location.pathname]} items={pages.filter((page) => page.title).map((page) => ({
        key: `/shop/${page.path}`, label: <Link to={`/shop/${page.path}`}>{page.title}</Link>,
      }))} />
    </Layout.Header>
    <Layout.Content style={{ padding: CONTENT_PADDING, width: "100%", maxWidth: CONTENT_WIDTH, margin: "auto" }}>
      <Suspense fallback={<Spin />}><Routes>
        {pages.map((page) => <Route key={page.path} path={page.path || "/"}
          element={page.public || getToken() ? page.page : <Navigate to="/shop/account" replace />} />)}
        <Route path="*" element={<Typography.Text>该商城功能未启用</Typography.Text>} />
      </Routes></Suspense>
    </Layout.Content>
  </Layout>;
}
