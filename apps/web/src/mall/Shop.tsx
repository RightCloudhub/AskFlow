import { Suspense, lazy } from "react";
import { Layout, Spin } from "antd";
import { Link, Navigate, Route, Routes, useLocation } from "react-router-dom";
import { getToken } from "../api/client";
import { useFeatures } from "../plugins/features";
import { ShopNavigation } from "./shop-navigation";
import { MallEmpty } from "./presentation";
import { BrandMark } from "../components/layout/BrandMark";
import "../styles/mall.css";

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
  const auth = location.pathname === "/shop/account" && !getToken();
  return <Layout className={`af-shop ${auth ? "af-shop--auth" : ""}`}>
    <ShopNavigation pages={pages} pathname={location.pathname} />
    <Layout.Content className="af-shop-content">
      <Suspense fallback={<div className="af-query-state"><Spin description="正在加载商城…" /></div>}><Routes>
        {pages.map((page) => <Route key={page.path} path={page.path || "/"}
          element={page.public || getToken() ? page.page : <Navigate to="/shop/account" replace />} />)}
        <Route path="*" element={<MallEmpty title="该商城功能未启用"><Link to="/shop">返回商城</Link></MallEmpty>} />
      </Routes></Suspense>
    </Layout.Content>
    <footer className="af-shop-footer"><Link to="/shop" className="af-shop-brand"><BrandMark /><span>AskFlow 商城</span></Link>
      <span>商品、订单与售后服务</span></footer>
  </Layout>;
}
