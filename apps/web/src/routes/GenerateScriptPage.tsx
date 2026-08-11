import { useMutation, useQueries } from "@tanstack/react-query";
import { FormEvent, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { ApiProblem, api } from "../api/client";

function idempotencyKey(productId: string, signature: string) {
  const storageKey = generationStorageKey(productId, signature);
  const existing = sessionStorage.getItem(storageKey);
  if (existing) return existing;
  const created = globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random()}`;
  sessionStorage.setItem(storageKey, created);
  return created;
}

function generationStorageKey(productId: string, signature: string) {
  return `generation:${productId}:${signature}`;
}

export function GenerateScriptPage() {
  const { id = "" } = useParams();
  const navigate = useNavigate();
  const [duration, setDuration] = useState(15);
  const [language, setLanguage] = useState("en");
  const [audience, setAudience] = useState("busy professionals");
  const [pattern, setPattern] = useState("problem_solution");
  const [productQuery, patternsQuery] = useQueries({
    queries: [
      { queryKey: ["product", id], queryFn: () => api.getProduct(id), enabled: Boolean(id) },
      { queryKey: ["creative-patterns"], queryFn: api.getPatterns },
    ],
  });
  const readyFacts = useMemo(
    () => productQuery.data?.facts.filter((fact) => fact.status === "confirmed" || fact.status === "locked") ?? [],
    [productQuery.data],
  );
  const generation = useMutation({
    mutationFn: () => {
      const input = { target_duration_seconds: duration, language, audience, creative_pattern_key: pattern };
      return api.createGeneration(id, input, idempotencyKey(id, JSON.stringify(input)));
    },
    onSuccess: (job) => {
      const input = { target_duration_seconds: duration, language, audience, creative_pattern_key: pattern };
      sessionStorage.removeItem(generationStorageKey(id, JSON.stringify(input)));
      navigate(`/jobs/${job.id}`);
    },
  });
  const error = generation.error as ApiProblem | null;
  function submit(event: FormEvent) { event.preventDefault(); generation.mutate(); }

  if (productQuery.isPending || patternsQuery.isPending) return <section className="page"><div className="state-card">正在准备生成合同…</div></section>;
  return (
    <section className="page form-page">
      <p className="eyebrow">GENERATION CONTRACT</p>
      <h1>配置事实脚本</h1>
      <p className="lede">只把已确认或锁定的事实交给 Provider；其他字段不会进入生成输入。</p>
      <form className="editor-form" onSubmit={submit}>
        <div className="field-row generation-fields">
          <label>目标时长<select value={duration} onChange={(event) => setDuration(Number(event.target.value))}><option value={15}>15 秒</option><option value={30}>30 秒</option><option value={45}>45 秒</option></select></label>
          <label>语言<select value={language} onChange={(event) => setLanguage(event.target.value)}><option value="en">English</option><option value="zh-CN">简体中文</option></select></label>
          <label>创意结构<select value={pattern} onChange={(event) => setPattern(event.target.value)}>{patternsQuery.data?.map((item) => <option key={item.key} value={item.key}>{item.name}</option>)}</select></label>
        </div>
        <label>目标受众<input required value={audience} onChange={(event) => setAudience(event.target.value)} /></label>
        <div><p className="eyebrow">SUPPORTED FACTS · {readyFacts.length}</p><div className="fact-preview">{readyFacts.map((fact) => <div key={fact.id}><span>{fact.status}</span><strong>{fact.claim}</strong><small>{fact.evidence_excerpt}</small></div>)}</div></div>
        {readyFacts.length === 0 && <div className="inline-error">没有可用事实。请先确认或锁定至少一条事实。</div>}
        {error && <div className="inline-error" role="alert">{error.message}</div>}
        <div className="form-actions"><button className="button button-primary" disabled={!readyFacts.length || generation.isPending}>创建生成任务</button></div>
      </form>
    </section>
  );
}
