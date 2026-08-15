import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FormEvent, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { ApiProblem, FactStatus, ProductFact, api } from "../api/client";

const STATUS_LABEL: Record<FactStatus, string> = {
  proposed: "待确认事实",
  confirmed: "已确认",
  rejected: "已否决",
  locked: "已锁定",
};

function FactRow({ productId, fact }: { productId: string; fact: ProductFact }) {
  const queryClient = useQueryClient();
  const transition = useMutation({
    mutationFn: (status: FactStatus) => api.transitionFact(productId, fact.id, status),
    onSuccess: async () => queryClient.invalidateQueries({ queryKey: ["product", productId] }),
  });
  const error = transition.error as ApiProblem | null;
  return (
    <article className="fact-row">
      <div className="fact-meta">
        <span className={`status status-${fact.status}`}>{STATUS_LABEL[fact.status]}</span>
        <span>{fact.claim_type}</span>
        <span>可信度 {Math.round(Number(fact.confidence) * 100)}%</span>
      </div>
      <h3>{fact.claim}</h3>
      <blockquote>{fact.evidence_excerpt}</blockquote>
      <p className="evidence-path">证据：{fact.evidence_kind} · {fact.evidence_locator}</p>
      <div className="fact-actions">
        {fact.status !== "locked" && <>
          <button type="button" onClick={() => transition.mutate("confirmed")}>确认</button>
          <button type="button" onClick={() => transition.mutate("rejected")}>否决</button>
          <button type="button" onClick={() => transition.mutate("locked")}>锁定</button>
        </>}
      </div>
      {error && <div className="inline-error" role="alert">{error.message}</div>}
    </article>
  );
}

function PromotionFactForm({ productId }: { productId: string }) {
  const queryClient = useQueryClient();
  const [kind, setKind] = useState<"percent_off" | "amount_off">("percent_off");
  const [percent, setPercent] = useState("");
  const [amount, setAmount] = useState("");
  const [effectiveFrom, setEffectiveFrom] = useState("");
  const [effectiveTo, setEffectiveTo] = useState("");
  const [evidence, setEvidence] = useState("");
  const create = useMutation({
    mutationFn: () => api.createPromotionFact(productId, {
      value: kind === "percent_off"
        ? { schema_version: "promotion-v1", kind, percent, market: "US", channel: "tiktok_shop", timezone: "America/Los_Angeles", effective_from: effectiveFrom, effective_to: effectiveTo }
        : { schema_version: "promotion-v1", kind, amount, currency: "USD", market: "US", channel: "tiktok_shop", timezone: "America/Los_Angeles", effective_from: effectiveFrom, effective_to: effectiveTo },
      evidence_excerpt: evidence,
    }, crypto.randomUUID()),
    onSuccess: async () => queryClient.invalidateQueries({ queryKey: ["product", productId] }),
  });
  function submit(event: FormEvent) {
    event.preventDefault();
    create.mutate();
  }
  return <form className="editor-form promotion-fact-form" onSubmit={submit}>
    <div className="section-heading"><div><p className="eyebrow">PROMOTION FACT</p><h2>受控优惠事实</h2></div><span>仅 TikTok Shop US · 最终 CTA</span></div>
    <p className="selection-help">优惠码、原价、倒计时、限量和自由促销文案不被支持。确认或锁定后才可用于有效期内的最终 CTA。</p>
    <div className="field-row"><label>优惠类型<select value={kind} onChange={(event) => setKind(event.target.value as typeof kind)}><option value="percent_off">百分比优惠</option><option value="amount_off">固定金额优惠</option></select></label><label>{kind === "percent_off" ? "百分比" : "金额（USD）"}<input required inputMode="decimal" value={kind === "percent_off" ? percent : amount} onChange={(event) => kind === "percent_off" ? setPercent(event.target.value) : setAmount(event.target.value)} /></label></div>
    <div className="field-row"><label>开始（含 UTC offset）<input required placeholder="2026-08-14T09:00:00-07:00" value={effectiveFrom} onChange={(event) => setEffectiveFrom(event.target.value)} /></label><label>结束（含 UTC offset）<input required placeholder="2026-08-15T23:59:59-07:00" value={effectiveTo} onChange={(event) => setEffectiveTo(event.target.value)} /></label></div>
    <label>人工证据摘录<textarea required value={evidence} onChange={(event) => setEvidence(event.target.value)} /></label>
    {create.error instanceof Error && <div className="inline-error" role="alert">{create.error.message}</div>}
    <div className="form-actions"><button className="button button-secondary" disabled={create.isPending}>添加 Promotion Fact</button></div>
  </form>;
}

export function ProductDetailPage() {
  const { id = "" } = useParams();
  const product = useQuery({ queryKey: ["product", id], queryFn: () => api.getProduct(id), enabled: Boolean(id) });
  if (product.isPending) return <section className="page"><div className="state-card">正在恢复商品快照…</div></section>;
  if (product.isError) return <section className="page"><div className="state-card state-error">商品不存在或暂时无法读取。</div></section>;
  const data = product.data;
  const readyFacts = data.facts.filter((fact) => fact.status === "confirmed" || fact.status === "locked").length;
  return (
    <section className="page page-wide">
      <Link className="back-link" to="/products">← 返回商品</Link>
      <div className="detail-hero">
        <div><p className="eyebrow">IMMUTABLE SNAPSHOT</p><h1>{data.snapshot.title}</h1><p>{data.snapshot.description || "暂无描述"}</p></div>
        <div className="snapshot-stamp"><span>摘要</span><code>{data.snapshot.canonical_digest.slice(0, 12)}</code><span>{new Date(data.snapshot.created_at).toLocaleString("zh-CN")}</span></div>
      </div>
      <div className="metrics-strip">
        <div><strong>{data.facts.length}</strong><span>全部事实</span></div>
        <div><strong>{readyFacts}</strong><span>可用于脚本</span></div>
        <div><strong>{data.snapshot.price_amount || "—"}</strong><span>{data.snapshot.price_currency || "未设置价格"}</span></div>
        <Link className="button button-primary" to={`/products/${id}/generate`}>生成脚本</Link>
      </div>
      <div className="section-heading"><div><p className="eyebrow">EVIDENCE LEDGER</p><h2>事实台账</h2></div><span>仅 confirmed / locked 事实可以支持商品声明</span></div>
      {data.facts.length === 0 ? <div className="empty-state compact"><h2>暂无事实</h2><p>为商品补充有证据的事实后再生成脚本。</p></div> : <div className="fact-list">{data.facts.map((fact) => <FactRow key={fact.id} productId={id} fact={fact} />)}</div>}
      <PromotionFactForm productId={id} />
    </section>
  );
}
