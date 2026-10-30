import { useState } from "react";
import { Button, Drawer } from "antd";
import { AppstoreOutlined, CreditCardOutlined, GiftOutlined, InboxOutlined, MenuOutlined,
  MessageOutlined, ShoppingCartOutlined, ShoppingOutlined, UserOutlined } from "@ant-design/icons";
import { Link } from "react-router-dom";
import { getToken } from "../api/client";
import { BrandMark } from "../components/layout/BrandMark";
import { WorkspaceSwitcher } from "../components/layout/WorkspaceSwitcher";

export type ShopDestination = { path: string; title?: string };
type NavigationProps = { pages: ShopDestination[]; pathname: string };
const GROUPS = [
  { title: "购买", paths: ["", "cart", "orders", "refunds"] },
  { title: "服务", paths: ["messages", "wallet", "referral"] },
  { title: "我的", paths: ["account"] },
];
const ICONS: Record<string, React.ReactNode> = {
  "": <AppstoreOutlined />, cart: <ShoppingCartOutlined />, orders: <ShoppingOutlined />, refunds: <InboxOutlined />,
  messages: <MessageOutlined />, wallet: <CreditCardOutlined />, referral: <GiftOutlined />, account: <UserOutlined />,
};

function selected(path: string, pathname: string) {
  if (!path) return pathname === "/shop" || pathname === "/shop/" || pathname.startsWith("/shop/products/");
  if (path === "cart") return pathname === "/shop/cart" || pathname === "/shop/checkout";
  return pathname.startsWith(`/shop/${path}`);
}

function ShopLinks({ pages, pathname, close }: NavigationProps & { close?: () => void }) {
  return <nav aria-label="商城导航" className="af-shop-links">{GROUPS.map((group) => {
    const destinations = pages.filter((page) => page.title && group.paths.includes(page.path));
    if (!destinations.length) return null;
    return <div key={group.title} className="af-shop-nav-group"><p>{group.title}</p>
      {destinations.map((page) => <Link key={page.path} to={`/shop/${page.path}`}
        aria-current={selected(page.path, pathname) ? "page" : undefined} onClick={close}>
        {ICONS[page.path]}<span>{page.title}</span></Link>)}
    </div>;
  })}</nav>;
}

export function ShopNavigation(props: NavigationProps) {
  const [open, setOpen] = useState(false);
  return <><header className="af-shop-header"><div className="af-shop-header-inner">
    <Link className="af-shop-brand" to="/shop"><BrandMark /><span>AskFlow <span className="af-shop-brand-scope">商城与服务</span></span></Link>
    <div className="af-shop-header-actions"><Link to="/shop/account"><Button type="text" icon={<UserOutlined />}>{getToken() ? "我的账号" : "登录 / 注册"}</Button></Link>
      <Button className="af-shop-menu-button" type="text" icon={<MenuOutlined />} aria-label="打开商城导航" onClick={() => setOpen(true)} />
    </div></div></header>
    <aside className="af-shop-sidebar"><WorkspaceSwitcher current="shop" /><ShopLinks {...props} />
      <p className="af-shop-nav-foot">购买与服务，一路相连。</p></aside>
    <Drawer className="af-shop-drawer" title="AskFlow 商城" placement="left" open={open} onClose={() => setOpen(false)}>
      <WorkspaceSwitcher current="shop" /><ShopLinks {...props} close={() => setOpen(false)} />
    </Drawer>
  </>;
}
