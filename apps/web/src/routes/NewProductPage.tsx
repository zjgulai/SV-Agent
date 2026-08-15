import { useMutation, useQueryClient } from "@tanstack/react-query";
import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";

import { ApiResponseParseError, api } from "../api/client";
import {
  beginOperation,
  findUnknownOperation,
  markOperationAccepted,
  markOperationRecovering,
  markOperationUnknown,
  type OperationRecord,
} from "../features/operationRecovery";

const IMPORT_ROUTE = "/api/v1/product-imports";

function importUrl(record: OperationRecord) {
  const body = record.request.body as { url?: unknown };
  return typeof body.url === "string" ? body.url : null;
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
  const [recoverableImport, setRecoverableImport] = useState(() =>
    findUnknownOperation("product_import", IMPORT_ROUTE),
  );

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
    mutationFn: async (operation: OperationRecord) => {
      const operationUrl = importUrl(operation);
      if (!operationUrl) throw new Error("恢复记录无效，请重新开始安全导入。");
      try {
        const job = await api.importProduct(operationUrl, operation.idempotency_key);
        const jobPath = `/jobs/${job.id}`;
        markOperationAccepted(operation.idempotency_key, jobPath);
        return jobPath;
      } catch (error) {
        const jobPath = error instanceof ApiResponseParseError ? error.jobPath : null;
        if (jobPath) {
          markOperationAccepted(operation.idempotency_key, jobPath);
          return jobPath;
        }
        markOperationUnknown(operation.idempotency_key);
        throw error;
      }
    },
    onSuccess: (jobPath) => {
      setRecoverableImport(null);
      navigate(jobPath);
    },
    onError: (_error, operation) => {
      setRecoverableImport(findUnknownOperation("product_import", operation.request.route) ?? operation);
    },
  });
  const error = manual.error || productImport.error;

  function submit(event: FormEvent) {
    event.preventDefault();
    if (mode === "manual") manual.mutate();
    else {
      const operation = beginOperation("product_import", {
        route: IMPORT_ROUTE,
        body: { url: url.trim() },
      });
      setRecoverableImport(null);
      productImport.mutate(operation);
    }
  }

  function recoverImport() {
    if (!recoverableImport) return;
    const operation = markOperationRecovering(recoverableImport.idempotency_key) ?? recoverableImport;
    setRecoverableImport(operation);
    productImport.mutate(operation);
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
        {error instanceof Error && <div className="inline-error" role="alert">{error.message}</div>}
        {mode === "url" && recoverableImport && (
          <div className="state-card recovery-card" role="status">
            <strong>请求状态未知</strong>
            <p>网络未确认本次安全导入的受理结果。恢复会使用原始请求与同一幂等键，不会创建新任务。</p>
            <button className="button button-secondary" type="button" disabled={productImport.isPending} onClick={recoverImport}>恢复原请求</button>
          </div>
        )}
        <div className="form-actions">
          <button className="button button-primary" disabled={manual.isPending || productImport.isPending} type="submit">
            {mode === "manual" ? "保存商品" : "开始安全导入"}
          </button>
        </div>
      </form>
    </section>
  );
}
