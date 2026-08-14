import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useParams } from "react-router-dom";

import { ApiProblem, api } from "../api/client";
import { ScriptTimeline } from "../features/scripts/ScriptTimeline";

function operationKey(storyboardId: string, decision: "approved" | "rejected", reason: string) {
  const storageKey = `storyboard-approval:${storyboardId}:${decision}:${reason.trim()}`;
  const existing = sessionStorage.getItem(storageKey);
  if (existing) return existing;
  const created = globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random()}`;
  sessionStorage.setItem(storageKey, created);
  return created;
}

export function StoryboardReviewPage() {
  const { id = "" } = useParams();
  const queryClient = useQueryClient();
  const [reason, setReason] = useState("");
  const storyboard = useQuery({ queryKey: ["storyboard", id], queryFn: () => api.getStoryboard(id), enabled: Boolean(id) });
  const preview = useQuery({ queryKey: ["storyboard-preview", id], queryFn: () => api.getStoryboardPreview(id), enabled: Boolean(id) });
  const approval = useQuery({ queryKey: ["storyboard-approval", id], queryFn: () => api.getStoryboardApproval(id), enabled: Boolean(id) });
  const decide = useMutation({
    mutationFn: (decision: "approved" | "rejected") => api.createStoryboardApproval(id, { decision, ...(reason.trim() ? { reason: reason.trim() } : {}) }, operationKey(id, decision, reason)),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["storyboard-approval", id] });
    },
  });
  if (storyboard.isPending || preview.isPending || approval.isPending) return <section className="page"><div className="state-card">正在恢复审核版分镜…</div></section>;
  if (storyboard.isError || preview.isError || approval.isError || !storyboard.data || !preview.data || !approval.data) {
    const error = (storyboard.error ?? preview.error ?? approval.error) as ApiProblem | null;
    return <section className="page"><div className="state-card state-error" role="alert">{error?.message ?? "审核版分镜不可用。"}</div></section>;
  }
  const current = approval.data;
  const decisionError = decide.error as ApiProblem | null;
  return (
    <section className="page page-wide storyboard-page storyboard-review-page">
      <Link className="back-link" to="/products">← 返回商品事实</Link>
      <div className="page-heading">
        <div><p className="eyebrow">DETERMINISTIC ANIMATIC · NO MEDIA</p><h1>审核版分镜</h1><p>此处是零成本、可重放的镜头合同预览；商品图片只作快照引用，不代表媒体生成或视觉质检通过。</p></div>
        <strong className={`preflight-status approval-${current.status}`}>{current.status === "approved" ? "已批准用于未来报价门禁" : current.status === "rejected" ? "已拒绝" : current.status === "stale" ? "批准已失效" : "等待本地审核"}</strong>
      </div>
      <div className="animatic-meta"><span>Preview digest · {preview.data.preview_digest.slice(0, 12)}</span><span>Pattern · {storyboard.data.pattern_key}@{storyboard.data.pattern_version}</span><span>图片引用 · {preview.data.image_indexes.length}</span></div>
      <section className="animatic-strip" aria-label="零成本 animatic 预览">
        {preview.data.shots.map((shot) => <article key={shot.index} className="animatic-card"><span>SHOT {shot.index} · {shot.start_seconds}–{shot.end_seconds}s</span><strong>{shot.phase_key}</strong><p>{shot.visual}</p><small>事实 {shot.supported_fact_ids.length} · {shot.caption || "无字幕"}</small></article>)}
      </section>
      <section className="storyboard-timeline"><div><p className="eyebrow">FROZEN SHOT CONTRACT</p><h2>不可变镜头合同</h2></div><ScriptTimeline shots={storyboard.data.draft.shots} /></section>
      <section className="approval-panel">
        <div><p className="eyebrow">LOCAL REVIEW ONLY</p><h2>人工审核</h2><p>批准仅进入未来报价前门禁；当前不提供报价、渲染、生成或发布。</p></div>
        <label>审核说明（可选，最多 500 字符）<textarea value={reason} maxLength={500} onChange={(event) => setReason(event.target.value)} rows={3} /></label>
        <div className="form-actions"><button type="button" className="button button-primary" disabled={decide.isPending || current.status === "stale"} onClick={() => decide.mutate("approved")}>批准</button><button type="button" disabled={decide.isPending || current.status === "stale"} onClick={() => decide.mutate("rejected")}>拒绝</button></div>
        {current.latest_event && <p className="approval-history">最近决定：{current.latest_event.decision} · 事件 #{current.latest_event.event_sequence}{current.latest_event.reason ? ` · ${current.latest_event.reason}` : ""}</p>}
        {decisionError && <p className="inline-error" role="alert">{decisionError.message}</p>}
      </section>
    </section>
  );
}
