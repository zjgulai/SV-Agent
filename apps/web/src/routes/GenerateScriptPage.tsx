import { useMutation, useQueries } from "@tanstack/react-query";
import { FormEvent, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { ApiResponseParseError, api, type ProductFact } from "../api/client";
import {
  beginOperation,
  findUnknownOperation,
  markOperationAccepted,
  markOperationRecovering,
  markOperationUnknown,
  type OperationRecord,
} from "../features/operationRecovery";

type GenerationInput = {
  target_duration_seconds: number;
  language: string;
  audience: "general" | "study_routine" | "work_routine" | "home_routine" | "on_the_go";
  creative_pattern_key: string;
  selected_fact_ids: string[];
  excluded_fact_ids: string[];
  promotion_fact_id: string | null;
};

function generationRoute(productId: string) {
  return `/api/v1/products/${productId}/script-generations`;
}

function promotionIsActive(fact: ProductFact, now = Date.now()) {
  const effectiveFrom = fact.value.effective_from;
  const effectiveTo = fact.value.effective_to;
  if (typeof effectiveFrom !== "string" || typeof effectiveTo !== "string") return false;
  const startsAt = Date.parse(effectiveFrom);
  const endsAt = Date.parse(effectiveTo);
  return Number.isFinite(startsAt) && Number.isFinite(endsAt) && startsAt <= now && now < endsAt;
}

export function GenerateScriptPage() {
  const { id = "" } = useParams();
  const navigate = useNavigate();
  const [duration, setDuration] = useState(15);
  const [language, setLanguage] = useState("en");
  const [audience, setAudience] = useState<GenerationInput["audience"]>("general");
  const [pattern, setPattern] = useState("problem_solution");
  const [selectedFactIds, setSelectedFactIds] = useState<string[]>([]);
  const [excludedFactIds, setExcludedFactIds] = useState<string[]>([]);
  const [promotionFactId, setPromotionFactId] = useState<string | null>(null);
  const [recoverableGeneration, setRecoverableGeneration] = useState(() =>
    findUnknownOperation("script_generation", generationRoute(id)),
  );
  const [productQuery, patternsQuery] = useQueries({
    queries: [
      { queryKey: ["product", id], queryFn: () => api.getProduct(id), enabled: Boolean(id) },
      { queryKey: ["creative-patterns"], queryFn: api.getPatterns },
    ],
  });
  const readyFacts = useMemo(
    () => productQuery.data?.facts.filter((fact) => (fact.status === "confirmed" || fact.status === "locked") && fact.claim_type !== "promotion") ?? [],
    [productQuery.data],
  );
  const promotionFacts = useMemo(
    () => (productQuery.data?.facts ?? [])
      .filter((fact) => (fact.status === "confirmed" || fact.status === "locked") && fact.claim_type === "promotion")
      .map((fact) => ({ fact, active: promotionIsActive(fact) })),
    [productQuery.data],
  );
  const selectedFacts = useMemo(
    () => selectedFactIds.map((id) => readyFacts.find((fact) => fact.id === id)).filter(Boolean),
    [readyFacts, selectedFactIds],
  );
  const patternDefinition = useMemo(
    () => patternsQuery.data
      ?.find((item) => item.key === pattern)
      ?.contracts.find((item) => item.duration_seconds === duration && item.language === language),
    [duration, language, pattern, patternsQuery.data],
  );
  const patternBudgetWeight = patternDefinition?.shots.reduce(
    (total, shot) => total + shot.budget_weight,
    0,
  ) ?? 0;
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
  const generationInput: GenerationInput = {
    target_duration_seconds: duration,
    language,
    audience,
    creative_pattern_key: pattern,
    selected_fact_ids: selectedFactIds,
    excluded_fact_ids: excludedFactIds,
    promotion_fact_id: promotionFactId,
  };
  const generation = useMutation({
    mutationFn: async (operation: OperationRecord) => {
      const input = operation.request.body as GenerationInput;
      try {
        const job = await api.createGeneration(id, input, operation.idempotency_key);
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
      setRecoverableGeneration(null);
      navigate(jobPath);
    },
    onError: (_error, operation) => {
      setRecoverableGeneration(findUnknownOperation("script_generation", operation.request.route) ?? operation);
    },
  });
  const error = generation.error;
  function submit(event: FormEvent) {
    event.preventDefault();
    const operation = beginOperation("script_generation", {
      route: generationRoute(id),
      body: generationInput,
    });
    setRecoverableGeneration(null);
    generation.mutate(operation);
  }
  function recoverGeneration() {
    if (!recoverableGeneration) return;
    const operation = markOperationRecovering(recoverableGeneration.idempotency_key) ?? recoverableGeneration;
    setRecoverableGeneration(operation);
    generation.mutate(operation);
  }

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
        <label>受众创意槽<select value={audience} onChange={(event) => setAudience(event.target.value as GenerationInput["audience"])}><option value="general">通用日常</option><option value="study_routine">学习日常</option><option value="work_routine">工作日常</option><option value="home_routine">居家日常</option><option value="on_the_go">出行日常</option></select></label>
        {patternDefinition ? <section className="pattern-contract-preview" aria-label="冻结 Pattern 合同">
          <div className="pattern-contract-heading"><div><p className="eyebrow">FROZEN PATTERN · {patternDefinition.version}</p><h2>冻结 Pattern 合同</h2></div><span>{patternDefinition.hook_type}</span></div>
          <p>阶段、镜头角色、事实绑定和时长预算均已固定，创建后会随 generation 一同保存。</p>
          <div className="pattern-contract-plan">
            {patternDefinition.phases.map((phase, index) => {
              const phaseShots = patternDefinition.shots.filter((shot) => shot.phase_key === phase.key);
              return <div key={`${phase.key}-${index}`}><strong>{index + 1}. {phase.key}</strong><span className="pattern-contract-shots">{phaseShots.map((shot, shotIndex) => {
                const budget = patternBudgetWeight ? Math.round(shot.budget_weight / patternBudgetWeight * 100) : 0;
                return <span key={`${phase.key}-${shotIndex}`}>镜头 {shotIndex + 1} · {shot.role} · 必须绑定已选事实 · {budget}%</span>;
              })}</span></div>;
            })}
          </div>
          <div className="pattern-contract-boundaries"><span>受众仅影响服务端场景、道具与拍摄槽</span><span>{patternDefinition.cta_policy.mode === "server_promotion_final_cta" ? "可选优惠只进入最终 CTA" : "CTA 不含优惠"}</span><span>口播上限 {patternDefinition.speaking_rate.max} {patternDefinition.speaking_rate.unit === "words_per_second" ? "词/秒" : "汉字/秒"}</span></div>
        </section> : <div className="inline-error">当前 Pattern 没有可用的冻结合同，无法创建生成任务。</div>}
        {patternDefinition?.cta_policy.mode === "server_promotion_final_cta" && <label>Promotion Fact（仅最终 CTA）<select value={promotionFactId ?? ""} onChange={(event) => setPromotionFactId(event.target.value || null)}><option value="">不使用优惠</option>{promotionFacts.map(({ fact, active }) => <option key={fact.id} value={fact.id} disabled={!active}>{fact.claim}{active ? "" : "（当前不可用）"}</option>)}</select><small>仅限已确认或锁定、仍在有效期内的 TikTok Shop US 优惠；当前不可用的优惠不可选择，且不会进入口播或商品声明。</small></label>}
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
        {error instanceof Error && <div className="inline-error" role="alert">{error.message}</div>}
        {recoverableGeneration && <div className="state-card recovery-card" role="status"><strong>请求状态未知</strong><p>恢复会使用原始生成合同与同一幂等键，不会创建新脚本任务。</p><button className="button button-secondary" type="button" disabled={generation.isPending} onClick={recoverGeneration}>恢复原请求</button></div>}
        <div className="form-actions"><button className="button button-primary" disabled={!patternDefinition || !selectedFactIds.length || generation.isPending}>创建生成任务</button></div>
      </form>
    </section>
  );
}
