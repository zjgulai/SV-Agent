import { useMutation, useQuery } from "@tanstack/react-query";
import { Link, useNavigate, useParams } from "react-router-dom";

import { ApiProblem, api } from "../api/client";
import { ScriptTimeline } from "../features/scripts/ScriptTimeline";
import { ValidationPanel } from "../features/scripts/ValidationPanel";

function FactContract({
  label,
  facts,
}: {
  label: string;
  facts: Array<{ id: string; claim: string; evidence_excerpt: string; status: string }>;
}) {
  return (
    <section className="storyboard-fact-card">
      <p className="eyebrow">{label}</p>
      {facts.length === 0 ? <p className="empty-contract">无</p> : <ol>{facts.map((fact) => (
        <li key={fact.id}><strong>{fact.claim}</strong><small>{fact.status} · {fact.evidence_excerpt}</small></li>
      ))}</ol>}
    </section>
  );
}

export function StoryboardPreflightPage() {
  const { id = "", versionId = "" } = useParams();
  const navigate = useNavigate();
  const preflight = useQuery({
    queryKey: ["storyboard-preflight", id, versionId],
    queryFn: () => api.getStoryboardPreflight(id, versionId),
    enabled: Boolean(id && versionId),
  });
  const createStoryboard = useMutation({
    mutationFn: () => api.createStoryboard(id, versionId, globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random()}`),
    onSuccess: (storyboard) => navigate(`/storyboards/${storyboard.id}`),
  });
  const createError = createStoryboard.error as ApiProblem | null;
  if (preflight.isPending) return <section className="page"><div className="state-card">正在重检事实与分镜合同…</div></section>;
  if (preflight.isError || !preflight.data) {
    const error = preflight.error as ApiProblem | null;
    return <section className="page"><Link className="back-link" to={"/scripts/" + id}>← 返回脚本</Link><div className="state-card state-error" role="alert">{error?.message ?? "分镜预检暂不可用。"}</div></section>;
  }
  const data = preflight.data;
  const ready = data.status === "ready";
  return (
    <section className="page page-wide storyboard-page">
      <Link className="back-link" to={"/scripts/" + id + "?version=" + versionId}>← 返回脚本</Link>
      <div className="page-heading">
        <div><p className="eyebrow">READ-ONLY STORYBOARD PREFLIGHT</p><h1>事实约束分镜预检</h1><p>重新校验冻结事实合同后，才展示可供后续流程使用的分镜。这里不调用视频模型、不创建任务，也不能进入渲染。</p></div>
        <strong className={ready ? "preflight-status preflight-ready" : "preflight-status preflight-blocked"}>{ready ? "可供后续批准" : "当前版本不可进入渲染"}</strong>
      </div>
      <div className="storyboard-contract">
        <FactContract label={"纳入事实 · " + data.selected_facts.length + "（顺序即优先级）"} facts={data.selected_facts} />
        <FactContract label={"排除事实 · " + data.excluded_facts.length} facts={data.excluded_facts} />
      </div>
      <ValidationPanel acceptable={ready} findings={data.validation_report.findings} />
      <section className="storyboard-timeline">
        <div><p className="eyebrow">SHOT CONTRACT</p><h2>{ready ? "只读分镜时间线" : "已阻断的分镜草案"}</h2></div>
        <ScriptTimeline shots={data.shots} />
      </section>
      <section className="storyboard-next-step">
        <div><p className="eyebrow">P2.0 REVIEW GATE</p><h2>持久化审核版分镜</h2><p>冻结当前分镜与事实合同，再进入零成本 animatic 审核。此操作不会调用模型、创建任务、报价或渲染。</p></div>
        {ready ? <button className="button button-primary" type="button" onClick={() => createStoryboard.mutate()} disabled={createStoryboard.isPending}>创建审核版分镜</button> : <p className="inline-error">阻断项未清除，不能创建审核版分镜。</p>}
        {createError && <p className="inline-error" role="alert">{createError.message}</p>}
      </section>
    </section>
  );
}
