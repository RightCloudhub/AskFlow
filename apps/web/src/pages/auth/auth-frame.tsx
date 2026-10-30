import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { ArrowLeftOutlined, ArrowRightOutlined } from "@ant-design/icons";
import { BrandMark } from "../../components/layout/BrandMark";

type AuthFrameProps = { title: string; description: string; children: ReactNode; variant?: "service" | "commerce" };
const CONTENT = {
  service: {
    headline: "每一个问题，都有下一步。",
    description: "连接企业知识、智能助手与人工服务，让咨询顺畅地走向解决。",
    steps: ["带着问题开始", "找到可信依据", "继续跟进处理"],
    foot: "AskFlow · 企业智能客服",
  },
  commerce: {
    headline: "购买之后，服务继续。",
    description: "商品、订单与客服相连。每一次购买，每一步进度，都有处可寻。",
    steps: ["挑选合适商品", "跟进订单进度", "获得售后支持"],
    foot: "AskFlow · 商城与服务",
  },
};

export function AuthFrame({ title, description, children, variant = "service" }: AuthFrameProps) {
  const content = CONTENT[variant];
  return <div className="af-auth"><div className="af-auth-card">
    <aside className="af-auth-hero"><div className="af-auth-hero-brand"><BrandMark /><strong>AskFlow</strong></div>
      <div className="af-auth-hero-copy"><h2>{content.headline}</h2><p>{content.description}</p>
        <ul className="af-auth-journey">{content.steps.map((step) => <li key={step}><span>{step}</span><ArrowRightOutlined /></li>)}</ul>
      </div><span className="af-auth-hero-foot">{content.foot}</span>
    </aside><main className="af-auth-main"><div className="af-auth-mobile-brand"><BrandMark /><strong>AskFlow</strong></div>
      <header><h1 className="af-auth-title">{title}</h1><p className="af-auth-description">{description}</p></header>
      {children}
      {variant === "commerce" && <Link to="/shop" className="af-auth-back"><ArrowLeftOutlined />返回商品目录</Link>}
    </main>
  </div></div>;
}
