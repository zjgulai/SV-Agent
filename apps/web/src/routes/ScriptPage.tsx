import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useParams, useSearchParams } from "react-router-dom";

import { ApiProblem, api } from "../api/client";
import {
  factRebindOperation,
  latestFactRebindOperation,
  type FactBinding,
} from "../features/scripts/factRebindOperation";
import { ScriptTimeline } from "../features/scripts/ScriptTimeline";
import { ValidationPanel } from "../features/scripts/ValidationPanel";

const readyFactStatuses = new Set(["confirmed", "locked"]);

export function ScriptPage() {
  const { id = "" } = useParams();
  const [params, setParams] = useSearchParams();
  const queryClient = useQueryClient();
  const [bindings, setBindings] = useState<Record<string, string>>({});
  const script = useQuery({ queryKey: ["script", id], queryFn: () => api.getScript(id), enabled: Boolean(id) });
  const selectedId = params.get("version") ?? script.data?.versions.at(-1)?.id;
  const version = script.data?.versions.find((item) => item.id === selectedId) ?? script.data?.versions.at(-1);
  const selectedFacts = useMemo(
    () => script.data?.fact_contract.selected ?? [],
    [script.data?.fact_contract.selected],
  );
  const readyFacts = useMemo(
    () => selectedFacts.filter((fact) => readyFactStatuses.has(fact.status)),
    [selectedFacts],
  );
  const restoredBindings = useMemo(
    () => new Map(
      (version ? latestFactRebindOperation(id, version.id)?.fact_bindings ?? [] : [])
        .filter((binding) => readyFacts.some((fact) => fact.id === binding.fact_id))
        .map((binding) => [binding.shot_index, binding.fact_id]),
    ),
    [id, readyFacts, version],
  );
  const bindingFor = (index: number) => {
    if (!version || readyFacts.length === 0) return "";
    const key = `${version.id}:${index}`;
    const explicit = bindings[key];
    if (readyFacts.some((fact) => fact.id === explicit)) return explicit ?? "";
    const restored = restoredBindings.get(index);
    if (readyFacts.some((fact) => fact.id === restored)) return restored ?? "";
    const current = version.draft.shots[index]?.supported_fact_ids[0];
    return readyFacts.some((fact) => fact.id === current) ? current ?? "" : readyFacts[0]?.id ?? "";
  };
  const factBindings: FactBinding[] = version?.draft.shots.map((_, index) => ({
    shot_index: index,
    fact_id: bindingFor(index),
  })) ?? [];
  const rebindAllowed = Boolean(
    version
      && version.validation_report.acceptable
      && readyFacts.length === selectedFacts.length
      && factBindings.length > 0
      && factBindings.every((binding) => readyFacts.some((fact) => fact.id === binding.fact_id)),
  );
  const derive = useMutation({
    mutationFn: () => {
      if (!version || !rebindAllowed) throw new Error("当前版本或冻结事实不满足重绑条件");
      const operation = factRebindOperation(id, version.id, factBindings);
      return api.deriveVersion(
        id,
        version.id,
        { fact_bindings: operation.fact_bindings },
        operation.idempotency_key,
      );
    },
    onSuccess: async (created) => {
      await queryClient.invalidateQueries({ queryKey: ["script", id] });
      setParams({ version: created.id });
    },
  });

  if (script.isPending) return <section className="page"><div className="state-card">正在读取脚本版本…</div></section>;
  if (script.isError || !version) return <section className="page"><div className="state-card state-error">脚本尚无可查看版本。</div></section>;

  const exportBase = `/api/v1/scripts/${id}/versions/${version.id}/export`;
  const deriveError = derive.error as ApiProblem | Error | null;
  const factsReady = readyFacts.length === selectedFacts.length;
  return (
    <section className="page page-wide script-page">
      <div className="page-heading"><div><p className="eyebrow">SCRIPT · {id.slice(0, 8)}</p><h1>结构化脚本</h1><p>{script.data.generation.pattern_key}@{script.data.generation.pattern_version} · {version.draft.target_duration_seconds}s · {version.draft.audience}</p></div><div className="export-actions"><a className="button" href={`${exportBase}?format=json`}>导出 JSON</a><a className="button button-primary" href={`${exportBase}?format=markdown`}>导出 Markdown</a></div></div>
      <div className="version-bar"><label>脚本版本<select value={version.id} onChange={(event) => setParams({ version: event.target.value })}>{script.data.versions.map((item, index) => <option key={item.id} value={item.id}>Version {index + 1}{item.revision_kind === "fact_rebind" ? " · 事实重绑" : ""}</option>)}</select></label><div className="version-actions">{script.data.versions.length > 1 && <Link to={`/scripts/${id}/compare?left=${script.data.versions[0].id}&right=${version.id}`}>比较版本 →</Link>}</div></div>
      {deriveError && <div className="inline-error" role="alert">{deriveError.message}</div>}
      <div className="frozen-fact-contract"><span>冻结事实合同</span><strong>纳入 {selectedFacts.length} · 排除 {script.data.fact_contract.excluded.length}</strong><small>只允许为每个分镜改绑已冻结、仍可用的事实；服务端会重建旁白、字幕和商品主张。</small><Link to={`/scripts/${id}/versions/${version.id}/storyboard-preflight`}>分镜预检 →</Link></div>
      <ValidationPanel acceptable={version.validation_report.acceptable} findings={version.validation_report.findings} />
      <section className="fact-rebind-editor" aria-labelledby="fact-rebind-heading">
        <div><p className="eyebrow">FACT-BOUND REVISION</p><h2 id="fact-rebind-heading">按分镜重绑事实</h2><p>不编辑标题、时间线或自由文案。每次保存都会附加一个新版本，旧版本保持不变。</p></div>
        {!version.validation_report.acceptable ? <p className="inline-error">当前父版本未通过校验，不能派生重绑版本。</p> : !factsReady ? <p className="inline-error">冻结事实已不再全部可用，需先恢复事实合同后才能重绑。</p> : <><div className="fact-rebind-list">{version.draft.shots.map((shot, index) => <label key={`${version.id}-${index}`}>分镜 {index + 1} · {shot.phase_key}<select aria-label={`分镜 ${index + 1} 绑定事实`} value={bindingFor(index)} onChange={(event) => setBindings((current) => ({ ...current, [`${version.id}:${index}`]: event.target.value }))}>{readyFacts.map((fact) => <option key={fact.id} value={fact.id}>{fact.claim}</option>)}</select></label>)}</div><button className="button button-primary" type="button" onClick={() => derive.mutate()} disabled={derive.isPending || !rebindAllowed}>{derive.isPending ? "正在保存…" : "保存事实重绑版本"}</button></>}
        {version.revision_kind === "fact_rebind" && <small className="revision-provenance">事实重绑版本 · 固定合同摘要 {version.operation_input_digest?.slice(0, 12)}</small>}
      </section>
      <div className="script-columns"><section><p className="eyebrow">TIMELINE</p><ScriptTimeline shots={version.draft.shots} /></section><aside><p className="eyebrow">DELIVERY PACK</p><h2>标题</h2><ul>{version.draft.titles.map((item) => <li key={item}>{item}</li>)}</ul><h2>标签</h2><div className="tag-list">{version.draft.tags.map((item) => <span key={item}>#{item}</span>)}</div><h2>拍摄清单</h2><ol>{version.draft.shooting_list.map((item) => <li key={item}>{item}</li>)}</ol></aside></div>
    </section>
  );
}
