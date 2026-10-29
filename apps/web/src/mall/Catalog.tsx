import { useCallback, useState } from "react";
import { Button, Card, Col, Image, Input, Row, Select, Space, Typography } from "antd";
import { Link, useParams } from "react-router-dom";
import { mall, money, write } from "./client";
import { Feedback, useLoad, type Page } from "./shared";

type Sku = { id: string; spu_id: string; title: string; price_cents: number; currency: string };
type Product = { id: string; title: string; description: string; images: string[]; skus: Sku[] };
const COLUMNS = 8;
const GRID_GUTTER = 16;
const MOBILE_COLUMNS = 24;
const CARD_MARGIN = 12;
const SELECT_WIDTH = 240;

export function Catalog() {
  const [q, setQuery] = useState("");
  const [cursor, setCursor] = useState("");
  const loader = useCallback(() => mall<Page<Sku>>(`/catalog/search?q=${encodeURIComponent(q)}&cursor=${encodeURIComponent(cursor)}`), [q, cursor]);
  const query = useLoad(loader);
  return <Space direction="vertical" style={{ width: "100%" }}>
    <Typography.Title level={2}>挑选心仪好物</Typography.Title>
    <Input.Search placeholder="搜索商品" onSearch={(value) => { setQuery(value); setCursor(""); }} allowClear />
    <Feedback {...query} />
    <Row gutter={GRID_GUTTER}>{query.data?.items.map((item) => <Col key={item.id} xs={MOBILE_COLUMNS} md={COLUMNS}>
      <Card title={item.title} style={{ marginBlock: CARD_MARGIN }}>
        <Typography.Paragraph>{money(item.price_cents, item.currency)}</Typography.Paragraph>
        <Link to={`/shop/products/${item.spu_id}`}>查看商品</Link>
      </Card>
    </Col>)}</Row>
    {query.data?.items.length === 0 && <Typography.Text>暂无符合条件的商品</Typography.Text>}
    {query.data?.next_cursor && <Button onClick={() => setCursor(query.data!.next_cursor!)}>下一页</Button>}
  </Space>;
}

export function ProductDetail() {
  const { id } = useParams();
  const [selected, setSelected] = useState<string>();
  const [status, setStatus] = useState("");
  const loader = useCallback(() => mall<Product>(`/catalog/products/${id}`), [id]);
  const query = useLoad(loader);
  async function add() {
    const sku = selected ?? query.data?.skus[0]?.id;
    if (!sku) return;
    try { await write("/order/cart/items", { sku_id: sku, qty: 1 }, { method: "PUT" }); setStatus("已加入购物车"); }
    catch (reason) { setStatus(reason instanceof Error ? reason.message : "添加失败"); }
  }
  return <Card title={query.data?.title ?? "商品详情"}>
    <Feedback {...query} /><Typography.Paragraph>{query.data?.description}</Typography.Paragraph>
    <Image.PreviewGroup>{query.data?.images.map((url) => <Image key={url} src={url} alt={query.data?.title} width="12em" />)}</Image.PreviewGroup>
    <Space direction="vertical">
      <Select placeholder="选择规格" style={{ minWidth: SELECT_WIDTH }} value={selected} onChange={setSelected}
        options={query.data?.skus.map((sku) => ({ value: sku.id, label: `${sku.title} · ${money(sku.price_cents)}` }))} />
      <Button onClick={add} disabled={!query.data?.skus.length}>加入购物车</Button>
      <Typography.Text>{status}</Typography.Text><Link to="/shop/cart">前往购物车</Link>
    </Space>
  </Card>;
}
