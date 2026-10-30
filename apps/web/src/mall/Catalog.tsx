import { useCallback, useState } from "react";
import { Button, Input, Select, Skeleton } from "antd";
import { mall } from "./client";
import { Feedback, useLoad, type Page } from "./shared";
import { MallEmpty, MallPage } from "./presentation";
import { ProductCard, type CatalogSku } from "./product-card";
import { CursorNav, QueryRefresh, useCursor } from "./query-view";
export { ProductDetail } from "./ProductDetail";
const SKELETON_ROWS = 4;

export function Catalog() {
  const [q, setQuery] = useState("");
  const [input, setInput] = useState("");
  const [sort, setSort] = useState("id");
  const paging = useCursor();
  const loader = useCallback(() => mall<Page<CatalogSku>>(
    `/catalog/search?q=${encodeURIComponent(q)}&cursor=${encodeURIComponent(paging.cursor)}&sort=${sort}`
  ), [q, paging.cursor, sort]);
  const query = useLoad(loader);
  function search(value: string) { setInput(value); setQuery(value.trim()); paging.reset(); }
  return <MallPage title="商品目录" description="挑选商品，了解规格，再从订单继续获得服务。" className="af-catalog"
    actions={<QueryRefresh query={query} />}>
    <div className="af-catalog-toolbar">
      <Input.Search value={input} onChange={(event) => { setInput(event.target.value); if (!event.target.value) search(""); }}
        aria-label="搜索商品" placeholder="搜索商品名称或关键词" onSearch={search} allowClear />
      <Select aria-label="商品排序" value={sort} onChange={(value) => { setSort(value); paging.reset(); }} options={[
        { value: "id", label: "默认排序" }, { value: "price_asc", label: "价格从低到高" }, { value: "price_desc", label: "价格从高到低" },
      ]} />
    </div><Feedback {...query} />
    <div className="af-catalog-result-line"><span>{q ? `“${q}” 的搜索结果` : "全部在售商品"}</span>
      {query.data && <span>本页 {query.data.items.length} 件商品规格</span>}</div>
    {query.loading && !query.data && <Skeleton paragraph={{ rows: SKELETON_ROWS }} />}
    <div className="af-catalog-grid">{query.data?.items.map((item) => <ProductCard key={item.id} sku={item} />)}</div>
    {!query.loading && !query.error && query.data?.items.length === 0 && <MallEmpty title="暂无符合条件的商品">
      {q && <Button onClick={() => search("")}>查看全部商品</Button>}
    </MallEmpty>}
    <CursorNav paging={paging} nextCursor={query.data?.next_cursor} loading={query.loading} />
  </MallPage>;
}
