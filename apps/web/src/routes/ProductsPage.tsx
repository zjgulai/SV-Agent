import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { api } from "../api/client";

export function ProductsPage() {
  const products = useQuery({ queryKey: ["products"], queryFn: api.listProducts });

  return (
    <section className="page page-wide">
      <div className="page-heading">
        <div>
          <p className="eyebrow">PRODUCT TRUTH LAYER</p>
          <h1>商品事实</h1>
          <p>先固定证据与事实，再把创意交给 AI。</p>
        </div>
        <Link className="button button-primary" to="/products/new">
          新建商品
        </Link>
      </div>
      {products.isPending && <div className="state-card">正在读取商品…</div>}
      {products.isError && <div className="state-card state-error">商品读取失败，请稍后重试。</div>}
      {products.data?.length === 0 && (
        <div className="empty-state">
          <span>01</span>
          <h2>还没有商品事实</h2>
          <p>手动录入商品，或从公开 Schema.org Product 页面导入。</p>
          <Link className="text-link" to="/products/new">建立第一个商品 →</Link>
        </div>
      )}
      <div className="product-grid">
        {products.data?.map((product) => (
          <Link className="product-card" key={product.product_id} to={`/products/${product.product_id}`}>
            <div className="product-card-index">{String(product.facts.length).padStart(2, "0")} FACTS</div>
            <h2>{product.snapshot.title}</h2>
            <p>{product.snapshot.description || "暂无描述"}</p>
            <div className="product-card-footer">
              <span>{product.snapshot.price_amount ? `${product.snapshot.price_amount} ${product.snapshot.price_currency}` : "未设置价格"}</span>
              <span>查看事实 →</span>
            </div>
          </Link>
        ))}
      </div>
    </section>
  );
}
