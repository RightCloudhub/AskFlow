import { useState } from "react";
import { Button, Drawer } from "antd";
import { MenuOutlined } from "@ant-design/icons";
import { Link } from "react-router-dom";
import { BrandMark } from "../components/layout/BrandMark";

export type ShopDestination = { path: string; title?: string };
type NavigationProps = { pages: ShopDestination[]; pathname: string };

function selected(path: string, pathname: string) {
  if (!path) return pathname === "/shop" || pathname === "/shop/" || pathname.startsWith("/shop/products/");
  if (path === "cart") return pathname === "/shop/cart" || pathname === "/shop/checkout";
  return pathname.startsWith(`/shop/${path}`);
}

function ShopLinks({ pages, pathname, close }: NavigationProps & { close?: () => void }) {
  return <nav aria-label="商城导航" className="af-shop-links">
    {pages.filter((page) => page.title).map((page) => <Link key={page.path} to={`/shop/${page.path}`}
      aria-current={selected(page.path, pathname) ? "page" : undefined} onClick={close}>{page.title}</Link>)}
  </nav>;
}

export function ShopNavigation(props: NavigationProps) {
  const [open, setOpen] = useState(false);
  return <header className="af-shop-header"><div className="af-shop-header-inner">
    <Link className="af-shop-brand" to="/shop" aria-label="AskFlow 商城首页"><BrandMark /><span>AskFlow <span className="af-shop-brand-scope">商城</span></span></Link>
    <div className="af-shop-desktop-nav"><ShopLinks {...props} /></div>
    <Button className="af-shop-menu-button" type="text" icon={<MenuOutlined />} aria-label="打开商城导航"
      onClick={() => setOpen(true)} />
    <Drawer className="af-shop-drawer" title="AskFlow 商城" placement="right" open={open} onClose={() => setOpen(false)}>
      <ShopLinks {...props} close={() => setOpen(false)} />
    </Drawer>
  </div></header>;
}
