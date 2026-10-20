import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { useParams, useSearchParams } from "react-router-dom";

import {
  ApiProblem,
  api,
  type ComparisonCandidate,
  type ComparisonEvidence,
  type SemanticDifference,
} from "../api/client";

function displayValue(value: unknown, present: boolean) {
  if (!present) return "Missing";
  if (value === null) return "null";
  if (value === undefined) return "Unknown";
  return typeof value === "object" ? JSON.stringify(value) : String(value);
}

function CandidateCard({ label, candidate }: { label: "Control" | "Variant"; candidate: ComparisonCandidate }) {
  return (
    <article className="comparison-candidate">
      <div className="comparison-card-heading">
        <div><span>{label === "Control" ? "01" : "02"}</span><h2>{label}</h2></div>
        <span className={`comparison-health comparison-health-${candidate.storyboard_readiness}`}>
          Storyboard preflight · {candidate.storyboard_readiness.toUpperCase()}
        </span>
      </div>
      <code>{candidate.version_id}</code>
      <h3>{candidate.draft.titles[0] ?? "Untitled script"}</h3>
      <dl>
        <div><dt>Duration</dt><dd>{candidate.draft.target_duration_seconds}s</dd></div>
        <div><dt>Language</dt><dd>{candidate.draft.language}</dd></div>
        <div><dt>Shots</dt><dd>{candidate.draft.shots.length}</dd></div>
        <div><dt>Live script gate</dt><dd>{candidate.live_validation_report.acceptable ? "PASS" : "BLOCKED"}</dd></div>
      </dl>
      <small>Preflight ready 不代表 Render 或 Publish approval。</small>
    </article>
  );
}

function EvidenceCard({ label, evidence }: { label: string; evidence: ComparisonEvidence }) {
  return (
    <article className="comparison-evidence-card">
      <div><span>{label}</span><strong>{evidence.availability.toUpperCase()}</strong></div>
      <p>{evidence.limitation}</p><code>{evidence.source_reference}</code>
    </article>
  );
}

function DifferenceValues({ item }: { item: SemanticDifference }) {
  return <>
    <span className="sr-only">Control</span><del>{displayValue(item.control, item.control_present)}</del>
    <span className="sr-only">Variant</span><ins>{displayValue(item.variant, item.variant_present)}</ins>
  </>;
}

function ComparisonError({ error, retry }: { error: Error; retry: () => void }) {
  const problem = error instanceof ApiProblem ? error.problem : null;
  const retryable = problem === null || problem.status === 503;
  const prefix = problem?.status === 404
    ? "对比对象不存在"
    : problem?.status === 409
      ? "对比引用冲突"
      : problem?.status === 500
        ? "事实完整性校验失败"
        : "暂时无法读取权威事实";
  return <div className="inline-error" role="alert">
    <strong>{prefix}</strong><span>{error.message}</span>{problem && <code>{problem.code}</code>}
    {retryable && <button type="button" onClick={retry}>重试</button>}
  </div>;
}

function LegacyVersionComparison({ id, left, right }: { id: string; left: string; right: string }) {
  const referencesValid = Boolean(id && left && right);
  const comparison = useQuery({
    queryKey: ["script-diff", id, left, right],
    queryFn: () => api.compareVersions(id, left, right),
    enabled: referencesValid,
  });
  return <section className="page page-wide">
    <p className="eyebrow">FIELD-LEVEL DIFF</p><h1>版本差异</h1>
    {!referencesValid && <div className="state-card state-error" role="alert">缺少 Left 或 Right version reference，无法比较。</div>}
    {referencesValid && comparison.isPending && <div className="state-card">正在比较版本…</div>}
    {comparison.error && <ComparisonError error={comparison.error} retry={() => { void comparison.refetch(); }} />}
    {comparison.data && <div className="diff-grid">{(["changed", "added", "removed"] as const).map((kind) => <section key={kind}>
      <h2>{kind.toUpperCase()} · {comparison.data[kind].length}</h2>
      {comparison.data[kind].map((item) => <article className={`diff-item diff-${kind}`} key={item.path}>
        <code>{item.path}</code>
        {"left" in item && <><del>{displayValue(item.left, true)}</del><ins>{displayValue(item.right, true)}</ins></>}
        {"value" in item && <p>{displayValue(item.value, true)}</p>}
      </article>)}
    </section>)}</div>}
  </section>;
}

function CreativeComparison({ id, control, variant }: { id: string; control: string; variant: string }) {
  const referencesValid = Boolean(id && control && variant);
  const [lens, setLens] = useState<"script" | "storyboard" | "asset">("script");
  const comparison = useQuery({
    queryKey: ["creative-comparison", id, control, variant],
    queryFn: () => api.getCreativeComparison(id, control, variant),
    enabled: referencesValid,
  });
  return (
    <section className="page page-wide creative-comparison-page">
      <div className="comparison-hero">
        <div><p className="eyebrow">FACTFRAME · READ-ONLY DECISION WORKBENCH</p><h1>创意对比实验台</h1>
          <p className="lede">在同一 Product Truth 合同下审阅两个不可变 Script Version；不排名、不生成、不发布。</p></div>
        {comparison.data && <div className="comparison-statuses" aria-label="对比状态">
          <strong className={`comparison-state comparison-state-${comparison.data.readiness.state}`}>{comparison.data.readiness.state.replace("_", " ").toUpperCase()}</strong>
          {comparison.data.readiness.evidence_needs.length > 0 && <strong className="comparison-state comparison-state-evidence">NEEDS EVIDENCE</strong>}
        </div>}
      </div>
      {!referencesValid && <div className="state-card state-error" role="alert">缺少 Control 或 Variant reference，无法建立对比。</div>}
      {referencesValid && comparison.isPending && <div className="state-card">正在读取创意对比…</div>}
      {comparison.error && <ComparisonError error={comparison.error} retry={() => { void comparison.refetch(); }} />}
      {comparison.data && <>
        <section className="comparison-contract" aria-label="冻结合同状态">
          <span>Single variable · {comparison.data.readiness.single_variable_status}</span><span>Product Truth · {comparison.data.product_truth_gate.status}</span>
          <span>Disposition · {comparison.data.readiness.disposition}</span><code>{comparison.data.projection_digest.slice(0, 12)}</code>
        </section>
        <nav className="comparison-lenses" aria-label="对比视图">
          {(["script", "storyboard", "asset"] as const).map((item) => <button type="button" aria-pressed={lens === item}
            key={item} onClick={() => setLens(item)}>
            {item[0].toUpperCase() + item.slice(1)}
          </button>)}
        </nav>
        {comparison.data.readiness.blockers.length > 0 && <section className="comparison-blockers" aria-labelledby="comparison-blockers-title">
          <div className="section-heading"><h2 id="comparison-blockers-title">当前阻断</h2><span>{comparison.data.readiness.blockers.length} findings</span></div>
          {comparison.data.readiness.blockers.map((item) => <article key={`${item.context}-${item.code}-${item.path ?? "root"}`}>
            <code>{item.code}</code><p>{item.message}</p>{item.path && <small>{item.path}</small>}
          </article>)}
        </section>}
        {lens === "script" && <section aria-label="Script comparison lens" className="comparison-candidates">
          <CandidateCard label="Control" candidate={comparison.data.control} /><CandidateCard label="Variant" candidate={comparison.data.variant} />
        </section>}
        {lens === "storyboard" && <section aria-label="Storyboard comparison lens" className="comparison-lens-cards">
          <article><strong>Control storyboard preflight · {comparison.data.control.storyboard_readiness.toUpperCase()}</strong><p>{comparison.data.control.live_validation_report.findings.length} live findings</p></article>
          <article><strong>Variant storyboard preflight · {comparison.data.variant.storyboard_readiness.toUpperCase()}</strong><p>{comparison.data.variant.live_validation_report.findings.length} live findings</p></article>
        </section>}
        {lens === "asset" && <section aria-label="Asset comparison lens" className="comparison-lens-cards">
          <article><strong>Asset evidence · {comparison.data.asset_evidence.availability.toUpperCase()}</strong><p>{comparison.data.asset_evidence.limitation}</p></article>
        </section>}
        <section className="comparison-ledger" aria-labelledby="difference-ledger-title">
          <div className="section-heading"><h2 id="difference-ledger-title">Difference Ledger</h2><span>{comparison.data.differences.length} changes · complete view</span></div>
          {comparison.data.differences.length === 0 && <div className="empty-state compact">两个版本的可比较字段没有差异；single-variable 仍未验证。</div>}
          {comparison.data.differences.map((item) => <article className="comparison-difference" key={`${item.section}-${item.path}-${item.change}`}>
            <div><code>{item.path}</code><span>{item.kind.replaceAll("_", " ")}</span></div><DifferenceValues item={item} />
          </article>)}
        </section>
        <section className="comparison-evidence" aria-labelledby="evidence-drawer-title">
          <div className="section-heading"><h2 id="evidence-drawer-title">Evidence Drawer</h2><span>Missing is not zero</span></div>
          <div>
            <article className="comparison-evidence-card"><div><span>Product Truth</span><strong>{comparison.data.product_truth_gate.status.toUpperCase()}</strong></div>
              <p>{comparison.data.product_truth_gate.selected_facts.length} selected · {comparison.data.product_truth_gate.excluded_facts.length} excluded</p><code>{comparison.data.product_truth_gate.snapshot_id}</code></article>
            <EvidenceCard label="Performance" evidence={comparison.data.performance_evidence} /><EvidenceCard label="Experiment" evidence={comparison.data.experiment_evidence} />
            <EvidenceCard label="Asset" evidence={comparison.data.asset_evidence} />
          </div>
          <ul className="comparison-limitations" aria-label="当前证据限制">
            {comparison.data.limitations.map((item) => <li key={`${item.context}-${item.code}`}><code>{item.code}</code><span>{item.message}</span></li>)}
          </ul>
        </section>
      </>}
    </section>
  );
}

export function CompareVersionsPage() {
  const { id = "" } = useParams();
  const [params] = useSearchParams();
  const control = params.get("left") ?? "";
  const variant = params.get("right") ?? "";
  const labEnabled = import.meta.env.VITE_CREATIVE_COMPARISON_LAB !== "false";
  return labEnabled ? <CreativeComparison id={id} control={control} variant={variant} /> : <LegacyVersionComparison id={id} left={control} right={variant} />;
}
