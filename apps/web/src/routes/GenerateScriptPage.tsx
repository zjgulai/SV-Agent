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
  const [selectedFactIds, setSelectedFactIds] = useState<string[]>([]);
  const [excludedFactIds, setExcludedFactIds] = useState<string[]>([]);
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
  const selectedFacts = useMemo(
    () => selectedFactIds.map((id) => readyFacts.find((fact) => fact.id === id)).filter(Boolean),
    [readyFacts, selectedFactIds],
  );
  function setFactMode(factId: string, mode: "selected" | "excluded" | "unused") {
    setSelectedFactIds((current) => {
      const without = current.filter((id) => id !== factId);
      return mode === "selected" ? [...without, factId] : without;
    });
    setExcludedFactIds((current) => {
      const without = current.filter((id) => id !== factId);
      return mode === "excluded" ? [...without, factId] : without;
    });
  }
  function moveSelectedFact(factId: string, direction: -1 | 1) {
    setSelectedFactIds((current) => {
      const index = current.indexOf(factId);
      const target = index + direction;
      if (index < 0 || target < 0 || target >= current.length) return current;
      const next = [...current];
      [next[index], next[target]] = [next[target], next[index]];
      return next;
    });
  }
  const generationInput = {
    target_duration_seconds: duration,
    language,
    audience,
    creative_pattern_key: pattern,
    selected_fact_ids: selectedFactIds,
    excluded_fact_ids: excludedFactIds,
  };
  const inputSignature = JSON.stringify(generationInput);
  const generation = useMutation({
    mutationFn: () => api.createGeneration(id, generationInput, idempotencyKey(id, inputSignature)),
    onSuccess: (job) => {
      sessionStorage.removeItem(generationStorageKey(id, inputSignature));
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
      <p className="lede">选择顺序就是事实优先级；排除项会写入本次生成的可追溯 deny-set。</p>
      <form className="editor-form" onSubmit={submit}>
        <div className="field-row generation-fields">
          <label>目标时长<select value={duration} onChange={(event) => setDuration(Number(event.target.value))}><option value={15}>15 秒</option><option value={30}>30 秒</option><option value={45}>45 秒</option></select></label>
          <label>语言<select value={language} onChange={(event) => setLanguage(event.target.value)}><option value="en">English</option><option value="zh-CN">简体中文</option></select></label>
          <label>创意结构<select value={pattern} onChange={(event) => setPattern(event.target.value)}>{patternsQuery.data?.map((item) => <option key={item.key} value={item.key}>{item.name}</option>)}</select></label>
        </div>
        <label>目标受众<input required value={audience} onChange={(event) => setAudience(event.target.value)} /></label>
        <div className="fact-selection">
          <div className="fact-selection-heading">
            <div><p className="eyebrow">FACT SELECTION · {readyFacts.length}</p><h2>本次生成事实</h2></div>
            <span>纳入 {selectedFactIds.length} · 排除 {excludedFactIds.length}</span>
          </div>
          <p className="selection-help">仅纳入的事实会交给 Provider；排除会阻止该事实出现在所有可见脚本文案中。</p>
          <div className="fact-preview">
            {readyFacts.map((fact) => {
              const selectedIndex = selectedFactIds.indexOf(fact.id);
              const mode = selectedIndex >= 0 ? "selected" : excludedFactIds.includes(fact.id) ? "excluded" : "unused";
              return <div className={`fact-selection-row fact-selection-${mode}`} key={fact.id}>
                <div><span>{mode === "selected" ? `优先级 ${selectedIndex + 1}` : mode === "excluded" ? "明确排除" : "未使用"}</span><strong>{fact.claim}</strong><small>{fact.evidence_excerpt}</small></div>
                <div className="fact-selection-actions">
                  <button type="button" aria-pressed={mode === "selected"} onClick={() => setFactMode(fact.id, "selected")}>纳入</button>
                  <button type="button" aria-pressed={mode === "excluded"} onClick={() => setFactMode(fact.id, "excluded")}>排除</button>
                  <button type="button" aria-pressed={mode === "unused"} onClick={() => setFactMode(fact.id, "unused")}>不使用</button>
                  {selectedIndex >= 0 && <><button type="button" aria-label={`上移 ${fact.claim}`} disabled={selectedIndex === 0} onClick={() => moveSelectedFact(fact.id, -1)}>↑</button><button type="button" aria-label={`下移 ${fact.claim}`} disabled={selectedIndex === selectedFactIds.length - 1} onClick={() => moveSelectedFact(fact.id, 1)}>↓</button></>}
                </div>
              </div>;
            })}
          </div>
          {selectedFacts.length > 0 && <p className="selection-order">生成顺序：{selectedFacts.map((fact) => fact?.claim).join(" → ")}</p>}
        </div>
        {readyFacts.length === 0 && <div className="inline-error">没有可用事实。请先确认或锁定至少一条事实。</div>}
        {readyFacts.length > 0 && selectedFactIds.length === 0 && <div className="inline-error">请至少纳入一条事实后再创建生成任务。</div>}
        {error && <div className="inline-error" role="alert">{error.message}</div>}
        <div className="form-actions"><button className="button button-primary" disabled={!selectedFactIds.length || generation.isPending}>创建生成任务</button></div>
      </form>
    </section>
  );
}
