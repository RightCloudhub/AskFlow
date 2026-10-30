import { useCallback, useState } from "react";
import { Alert, Button, Image, Select } from "antd";
import { Link, useNavigate, useParams } from "react-router-dom";
import { getToken } from "../api/client";
import { useFeatures } from "../plugins/features";
import { mall, money, write } from "./client";
import { Feedback, useLoad } from "./shared";
import { MallEmpty, MallPage, MallPanel } from "./presentation";

type Sku = { id: string; title: string; price_cents: number; currency: string };
type Product = { title: string; description: string; images: string[]; skus: Sku[] };

function ProductGallery({ product }: { product: Product }) {
  if (!product.images.length) return <MallPanel title="商品说明" className="af-product-text-preview">
    <p>{product.description || product.title}</p>
  </MallPanel>;
  return <div className="af-product-gallery"><Image.PreviewGroup>
    {product.images.map((url, index) => <Image key={url} src={url} alt={`${product.title} · 商品图片 ${index + 1}`} />)}
  </Image.PreviewGroup></div>;
}

function ProductPurchase({ product }: { product: Product }) {
  const [selected, setSelected] = useState<string>();
  const [busy, setBusy] = useState(false);
  const [added, setAdded] = useState(false);
  const [error, setError] = useState("");
  const { enabled } = useFeatures();
  const navigate = useNavigate();
  const sku = product.skus.find((row) => row.id === selected) ?? product.skus[0];
  async function add() {
    if (!sku || busy) return;
    if (!getToken()) { navigate("/shop/account"); return; }
    setBusy(true); setError(""); setAdded(false);
    try { await write("/order/cart/items", { sku_id: sku.id, qty: 1 }, { method: "PUT" }); setAdded(true); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "添加失败"); }
    finally { setBusy(false); }
  }
  return <MallPanel title="选择商品规格" className="af-product-purchase">
    <p className="af-product-price">{sku ? money(sku.price_cents, sku.currency) : "暂无可售规格"}</p>
    <p className="af-product-description">{product.description}</p>
    <label className="af-field"><span>商品规格</span><Select aria-label="商品规格" value={sku?.id} disabled={!sku || busy}
      onChange={(value) => { setSelected(value); setAdded(false); }} options={product.skus.map((row) => ({
        value: row.id, label: `${row.title} · ${money(row.price_cents, row.currency)}`,
      }))} /></label>
    {enabled("mall_order") && <><Button type="primary" block disabled={!sku} loading={busy} onClick={() => void add()}>加入购物车</Button>
      <Link className="af-mall-text-link" to="/shop/cart">前往购物车</Link></>}
    <Feedback error={error} />{added && <Alert type="success" title="已加入购物车" showIcon />}
  </MallPanel>;
}

export function ProductDetail() {
  const { id } = useParams();
  const loader = useCallback(() => mall<Product>(`/catalog/products/${id}`), [id]);
  const query = useLoad(loader);
  return <MallPage title={query.data?.title ?? "商品详情"} actions={<Link to="/shop">返回商品目录</Link>}>
    <Feedback {...query} />
    {query.data && <div className="af-product-detail"><ProductGallery product={query.data} />
      <ProductPurchase key={id} product={query.data} /></div>}
    {!query.loading && !query.error && !query.data && <MallEmpty title="商品暂时不可用" />}
  </MallPage>;
}
