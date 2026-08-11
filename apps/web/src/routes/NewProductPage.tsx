import { useMutation, useQueryClient } from "@tanstack/react-query";
import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";

import { ApiProblem, api } from "../api/client";

const IMPORT_RETRY_KEY = "product-import:pending";

function importKey(url: string) {
  const normalizedUrl = url.trim();
  const stored = sessionStorage.getItem(IMPORT_RETRY_KEY);
  if (stored) {
    const pending = JSON.parse(stored) as { url: string; key: string };
    if (pending.url === normalizedUrl) return pending.key;
  }
  const key = crypto.randomUUID();
  sessionStorage.setItem(IMPORT_RETRY_KEY, JSON.stringify({ url: normalizedUrl, key }));
  return key;
}

export function NewProductPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [mode, setMode] = useState<"manual" | "url">("manual");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [category, setCategory] = useState("");
  const [price, setPrice] = useState("");
  const [currency, setCurrency] = useState("USD");
  const [url, setUrl] = useState("");

  const manual = useMutation({
    mutationFn: () =>
      api.createProduct({
        title,
        description,
        category_path: category ? category.split(">").map((item) => item.trim()) : [],
        images: [],
        ...(price ? { price: { amount: price, currency } } : {}),
        facts: description
          ? [
              {
                claim_type: "description",
                claim: description,
                value: { description },
                evidence_excerpt: description,
              },
            ]
          : [],
      }),
    onSuccess: async (product) => {
      await queryClient.invalidateQueries({ queryKey: ["products"] });
      navigate(`/products/${product.product_id}`);
    },
  });
  const productImport = useMutation({
    mutationFn: () => api.importProduct(url, importKey(url)),
    onSuccess: (job) => {
      sessionStorage.removeItem(IMPORT_RETRY_KEY);
      navigate(`/jobs/${job.id}`);
    },
  });
  const error = (manual.error || productImport.error) as ApiProblem | null;

  function submit(event: FormEvent) {
    event.preventDefault();
    if (mode === "manual") manual.mutate();
    else productImport.mutate();
  }

  return (
    <section className="page form-page">
      <p className="eyebrow">NEW PRODUCT SOURCE</p>
      <h1>建立商品事实源</h1>
      <p className="lede">信息会保存为不可变快照；后续修改将创建新版本。</p>
      <div className="segmented" role="tablist" aria-label="商品来源">
        <button type="button" className={mode === "manual" ? "active" : ""} onClick={() => setMode("manual")}>手动录入</button>
        <button type="button" className={mode === "url" ? "active" : ""} onClick={() => setMode("url")}>公开 URL 导入</button>
      </div>
      <form className="editor-form" onSubmit={submit}>
        {mode === "manual" ? (
          <>
            <label>商品名称<input required value={title} onChange={(event) => setTitle(event.target.value)} placeholder="例如 Pulse Mix" /></label>
            <label>商品描述<textarea required value={description} onChange={(event) => setDescription(event.target.value)} rows={5} placeholder="只填写可提供证据的客观描述" /></label>
            <div className="field-row">
              <label>品类路径<input value={category} onChange={(event) => setCategory(event.target.value)} placeholder="Food > Drink Mix" /></label>
              <label>价格<input inputMode="decimal" value={price} onChange={(event) => setPrice(event.target.value)} placeholder="19.90" /></label>
              <label>币种<input maxLength={3} value={currency} onChange={(event) => setCurrency(event.target.value.toUpperCase())} /></label>
            </div>
          </>
        ) : (
          <label>公开商品 URL<input required type="url" value={url} onChange={(event) => setUrl(event.target.value)} placeholder="https://example.com/product" /><small>仅支持公开 HTTP/HTTPS 页面中的 Schema.org Product，不执行 JavaScript。</small></label>
        )}
        {error && <div className="inline-error" role="alert">{error.message}</div>}
        <div className="form-actions">
          <button className="button button-primary" disabled={manual.isPending || productImport.isPending} type="submit">
            {mode === "manual" ? "保存商品" : "开始安全导入"}
          </button>
        </div>
      </form>
    </section>
  );
}
