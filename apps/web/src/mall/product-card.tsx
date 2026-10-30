import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ArrowRightOutlined } from "@ant-design/icons";
import { Link } from "react-router-dom";
import { mall, money } from "./client";

export type CatalogSku = { id: string; spu_id: string; title: string; price_cents: number; currency: string };
export type CatalogProduct = { title: string; description: string; images: string[]; skus: CatalogSku[] };
const PRODUCT_CACHE_MS = 60_000;

function ProductThumbnail({ product }: { product?: CatalogProduct }) {
  const [failed, setFailed] = useState(false);
  const source = product?.images?.[0];
  if (!source || failed) return <div className="af-product-no-image"><span>{product?.title || "商品"}</span><small>暂无商品图片</small></div>;
  return <img className="af-product-thumbnail" src={source} alt={product?.title || "商品图片"} loading="lazy" onError={() => setFailed(true)} />;
}

export function ProductCard({ sku }: { sku: CatalogSku }) {
  const product = useQuery({ queryKey: ["mall", "public-product", sku.spu_id],
    queryFn: () => mall<CatalogProduct>(`/catalog/products/${encodeURIComponent(sku.spu_id)}`),
    staleTime: PRODUCT_CACHE_MS, retry: 1 });
  return <article className="af-product-card"><Link to={`/shop/products/${sku.spu_id}`} className="af-product-card-link">
    <div className="af-product-card-media"><ProductThumbnail key={product.data?.images?.[0]} product={product.data} /></div>
    <div className="af-product-card-copy"><h2>{product.data?.title || sku.title}</h2>
      {product.data?.title && <p className="af-product-variant">{sku.title}</p>}
      <div className="af-product-card-bottom"><p className="af-product-price">{money(sku.price_cents, sku.currency)}</p>
        <span className="af-product-card-action">查看规格<ArrowRightOutlined /></span></div>
    </div>
  </Link></article>;
}
