import { useCallback, useState } from "react";
import { Button, Input, Select } from "antd";
import { Link } from "react-router-dom";
import { mall, money } from "./client";
import { Feedback, useLoad, type Page } from "./shared";
import { MallEmpty, MallPage } from "./presentation";
export { ProductDetail } from "./ProductDetail";

type Sku = { id: string; spu_id: string; title: string; price_cents: number; currency: string };

export function Catalog() {
  const [q, setQuery] = useState("");
  const [cursor, setCursor] = useState("");
  const [sort, setSort] = useState("id");
  const loader = useCallback(() => mall<Page<Sku>>(
    `/catalog/search?q=${encodeURIComponent(q)}&cursor=${encodeURIComponent(cursor)}&sort=${sort}`
  ), [q, cursor, sort]);
  const query = useLoad(loader);
  return <MallPage title="商品目录" description="查找商品、比较规格与价格，从这里开始。" className="af-catalog">
    <div className="af-catalog-toolbar">
      <Input.Search aria-label="搜索商品" placeholder="搜索商品名称或关键词"
        onSearch={(value) => { setQuery(value); setCursor(""); }} allowClear />
      <Select aria-label="商品排序" value={sort} onChange={(value) => { setSort(value); setCursor(""); }} options={[
        { value: "id", label: "默认排序" }, { value: "price_asc", label: "价格从低到高" }, { value: "price_desc", label: "价格从高到低" },
      ]} />
    </div>
    <Feedback {...query} />
    {q && <p className="af-mall-note">“{q}” 的搜索结果</p>}
    <div className="af-catalog-grid">{query.data?.items.map((item) => <article key={item.id} className="af-product-card">
      <Link to={`/shop/products/${item.spu_id}`} className="af-product-card-link">
        <h2>{item.title}</h2><p className="af-product-price">{money(item.price_cents, item.currency)}</p>
        <span className="af-product-card-action">查看商品与规格</span>
      </Link>
    </article>)}</div>
    {!query.loading && !query.error && query.data?.items.length === 0 && <MallEmpty title="暂无符合条件的商品">
      {q && <Button onClick={() => { setQuery(""); setCursor(""); }}>查看全部商品</Button>}
    </MallEmpty>}
    {query.data?.next_cursor && <div className="af-mall-pagination">
      <Button onClick={() => setCursor(query.data!.next_cursor!)}>下一页商品</Button>
    </div>}
  </MallPage>;
}
