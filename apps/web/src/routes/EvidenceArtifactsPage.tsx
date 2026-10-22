import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";

import {
  api,
  type EvidenceArtifactsProjection,
  type EvidenceArtifactType,
  type EvidenceAvailabilityState,
  type EvidencePlaneKind,
  type EvidenceSubjectSummary,
  type EvidenceWindowSummary,
} from "../api/client";
import "../features/sv-agent/styles/evidence-artifacts.css";

const artifactLabels: Record<EvidenceArtifactType, string> = {
  reference_bundle: "参考素材包",
  decomposition_map: "内容拆解图",
  pattern_hypothesis: "爆款机制假设",
  replication_plan: "复刻计划",
  fact_map: "事实绑定图",
  replication_contract: "不可变复刻合同",
  adaptation_package: "品牌适配包",
  media_integrity_record: "媒体完整性记录",
  replication_finding: "复刻结论",
};

const artifactStatusLabels: Record<EvidenceArtifactsProjection["graph"]["nodes"][number]["status"], string> = {
  draft: "草稿",
  validated: "已校验",
  awaiting_approval: "等待人工决定",
  blocked: "已阻断",
  approved: "已批准",
  stale: "已失效",
  superseded: "已被新版替代",
  final_with_limits: "有限制完成",
};

const evidenceLevelLabels: Record<EvidenceArtifactsProjection["graph"]["nodes"][number]["evidence_level"], string> = {
  fact: "直接事实",
  inference: "有边界的推断",
  unknown: "尚不明确",
};

const proofLevelLabels: Record<NonNullable<EvidenceArtifactsProjection["evidence_planes"][number]["proof_level"]>, string> = {
  local: "本地证明",
  ci: "公开 CI 证明",
  private: "私有库复验",
  deployment: "部署验证",
  live: "在线验证",
  production: "生产验收",
};

const sourceKindLabels: Record<string, string> = {
  public_url: "公开链接",
  local_media: "本地媒体记录",
  reviewed_package: "已审核证据包",
  product_truth: "商品事实库",
  experiment: "受控实验",
  asset_bundle: "素材包",
  human_observation: "人工观察",
  other: "其他受控来源",
};

const planeSourceLabels: Record<string, string> = {
  not_connected: "尚未连接已审核证据",
  no_product_claims: "本任务不包含商品声明",
  not_applicable: "本任务不包含商品声明",
  postgresql_product_truth: "PostgreSQL 商品事实库",
};

const planeLabels: Record<EvidencePlaneKind, string> = {
  product_truth: "Product Truth",
  performance: "Performance",
  experiment: "Experiment",
  asset: "Asset",
};

const stateLabels: Record<EvidenceAvailabilityState, string> = {
  available: "已有受控证据",
  unavailable: "当前不可用",
  out_of_scope: "本任务不适用",
  quarantined: "暂时隔离",
};

const subjectLabels: Record<EvidenceSubjectSummary["state"], string> = {
  exact_snapshot: "已精确绑定 Product Snapshot",
  reviewed_snapshot_selection: "已人工选定 Snapshot，但绑定范围有限",
  reviewed_family_context: "只确认到 Product Family 范围",
  unresolved: "主体尚未确定",
  conflict: "主体绑定存在冲突",
  not_applicable: "本任务不需要商品主体绑定",
};

const nonEffectLabels: Record<string, string> = {
  does_not_write_postgresql: "不会写入 PostgreSQL 或推进 Task / Run。",
  does_not_read_filesystem_or_private_assets: "不会读取本地文件系统或 Momcozy 私有素材库。",
  does_not_bind_external_evidence_packages: "不会自动绑定外部 Performance、Experiment 或 Asset 证据包。",
  does_not_infer_control_or_variant_versions: "不会猜测 Control / Variant，也不会把 generic ID 当成 ScriptVersion。",
  does_not_decide_approval: "不会代替人工作出任何审批决定。",
  does_not_render_or_publish: "不会生成、渲染、上传或发布视频。",
  does_not_establish_production_acceptance: "不会把本页结果当作商业或生产验收。",
};

const graphCopy: Record<string, string[]> = {
  RUN_NOT_STARTED: ["尚未创建权威 Run，因此没有可展示的产物图谱。"],
  ARTIFACT_GRAPH_EMPTY: ["当前 Run 还没有已校验的版本化产物。"],
  ARTIFACT_GRAPH_AVAILABLE: [
    "声明的产物依赖与运行时验证是两类不同证据。",
    "外部 Script、Storyboard 和媒体引用不会自动成为图谱中的权威产物。",
  ],
};

const planeCopy: Record<string, string[]> = {
  PRODUCT_TRUTH_EVIDENCE_UNAVAILABLE: ["没有可验证的 Product Snapshot / Product Fact 精确绑定。"],
  PRODUCT_TRUTH_OUT_OF_SCOPE: ["本任务不包含商品声明；若以后加入声明，必须重新绑定 Product Truth。"],
  PERFORMANCE_EVIDENCE_UNAVAILABLE: ["这里只记录任务声明的时间范围，没有连接已审核的表现数据包。"],
  EXPERIMENT_EVIDENCE_UNAVAILABLE: ["没有连接已审核的实验数据包，不能判断哪一版更好，也不能证明因果关系。"],
  EXPERIMENT_EVIDENCE_QUARANTINED: ["实验证据正在隔离复核，当前不能用于结论。"],
  ASSET_EVIDENCE_UNAVAILABLE: ["没有连接已批准的素材证据；Private Gate 也不等于商业批准。"],
};

function localizedPlaneLimitations(
  plane: EvidenceArtifactsProjection["evidence_planes"][number],
) {
  return planeCopy[plane.public_code] ?? plane.limitations;
}

function formatWindow(window: EvidenceWindowSummary | null) {
  if (!window) return "没有已绑定的观察时间窗";
  return `${window.start} 至 ${window.end}`;
}

function ArtifactDetails({
  node,
}: {
  node: EvidenceArtifactsProjection["graph"]["nodes"][number];
}) {
  return (
    <details className="evidence-details">
      <summary>查看{artifactLabels[node.artifact_type]}证据细节</summary>
      <dl>
        <div>
          <dt>来源</dt>
          <dd>
            {node.sources.length > 0
              ? node.sources.map((source) => sourceKindLabels[source.kind] ?? "受控来源").join("、")
              : "没有可公开的来源类型"}
          </dd>
        </div>
        <div>
          <dt>主体</dt>
          <dd>
            <span>{subjectLabels[node.subject.state]}</span>
            {(node.subject.market || node.subject.locale) && (
              <span>
                {[node.subject.market, node.subject.locale].filter(Boolean).join(" · ")}
              </span>
            )}
          </dd>
        </div>
        <div>
          <dt>时间窗</dt>
          <dd>
            <span>{formatWindow(node.window)}</span>
            {node.window && <small>{node.window.timezone}</small>}
          </dd>
        </div>
        <div>
          <dt>证明级别</dt>
          <dd>{proofLevelLabels[node.proof_level]}</dd>
        </div>
      </dl>
      {[...node.subject.limitations, ...node.limitations].length > 0 && (
        <ul>
          {[...node.subject.limitations, ...node.limitations].map((limitation) => (
            <li key={limitation}>{limitation}</li>
          ))}
        </ul>
      )}
      <details className="evidence-audit-details">
        <summary>查看审计引用</summary>
        <code>{node.ref}</code>
      </details>
    </details>
  );
}

function EvidencePlane({
  plane,
}: {
  plane: EvidenceArtifactsProjection["evidence_planes"][number];
}) {
  const limitations = localizedPlaneLimitations(plane);
  return (
    <article className={`evidence-plane evidence-plane-${plane.state}`}>
      <header>
        <div>
          <p className="eyebrow">独立证据面</p>
          <h3>{planeLabels[plane.kind]}</h3>
        </div>
        <span>{stateLabels[plane.state]}</span>
      </header>
      <p>{limitations[0] ?? "当前没有更多说明。"}</p>
      <details className="evidence-details">
        <summary>查看来源与限制</summary>
        <dl>
          <div><dt>来源</dt><dd>{planeSourceLabels[plane.source] ?? "受控证据来源"}</dd></div>
          <div>
            <dt>主体</dt>
            <dd>{plane.subject ? subjectLabels[plane.subject.state] : "没有已绑定主体"}</dd>
          </div>
          <div><dt>时间窗</dt><dd>{formatWindow(plane.window)}</dd></div>
          <div><dt>证明级别</dt><dd>{plane.proof_level ? proofLevelLabels[plane.proof_level] : "未形成证明"}</dd></div>
        </dl>
        {limitations.length > 0 && (
          <ul>
            {limitations.map((limitation) => <li key={limitation}>{limitation}</li>)}
          </ul>
        )}
        <code>{plane.public_code}</code>
      </details>
    </article>
  );
}

export function EvidenceArtifactsPage() {
  const { taskId } = useParams<"taskId">();
  const workspace = useQuery({
    queryKey: ["sv-agent", "evidence-artifacts", taskId],
    queryFn: () => api.getSvAgentEvidenceArtifacts(taskId!),
    enabled: Boolean(taskId),
  });

  if (!taskId) {
    return <div className="page state-card state-error" role="alert">Task 标识缺失。</div>;
  }
  if (workspace.isPending) {
    return <div className="page state-card">正在读取证据与产物…</div>;
  }
  if (workspace.isError || !workspace.data) {
    return (
      <section className="page">
        <Link className="back-link" to={`/sv-agent/tasks/${encodeURIComponent(taskId)}`}>
          ← 返回 Mission Control
        </Link>
        <div className="state-card state-error" role="alert">
          <h1>无法读取证据与产物</h1>
          <p>没有 Task、Run、Artifact 或审批被修改。</p>
          <button className="button button-secondary" onClick={() => workspace.refetch()} type="button">
            重新读取
          </button>
        </div>
      </section>
    );
  }

  const data = workspace.data;
  const conclusionCount = data.graph.nodes.filter((node) => node.is_conclusion).length;
  const unavailablePlaneCount = data.evidence_planes.filter(
    (plane) => plane.state !== "available",
  ).length;
  const nodesByRef = new Map(data.graph.nodes.map((node) => [node.ref, node]));
  const graphLimitations = graphCopy[data.graph.public_code] ?? data.graph.limitations;
  const canCompare =
    data.comparison.state === "available"
    && Boolean(data.comparison.script_ref)
    && Boolean(data.comparison.control_version_ref)
    && Boolean(data.comparison.variant_version_ref);

  return (
    <section className="evidence-page">
      <div className="evidence-frame">
        <header className="evidence-hero">
          <div>
            <Link className="back-link" to={`/sv-agent/tasks/${encodeURIComponent(taskId)}`}>
              ← 返回 Mission Control
            </Link>
            <p className="eyebrow">SV-AGENT · EVIDENCE &amp; ARTIFACTS</p>
            <h1>{data.task.subject}的证据与产物</h1>
            <p>先看证据能支持什么，再看产物如何相互依赖。缺失数据会保留原义，不会被写成零。</p>
          </div>
          <div className="evidence-authority">
            <strong>PostgreSQL 权威投影</strong>
            <span>Task revision {data.task.task_revision}</span>
            <span>{data.run ? `Run revision ${data.run.run_revision}` : "尚未创建 Run"}</span>
            <Link to={`/sv-agent/tasks/${encodeURIComponent(taskId)}/approval-replay`}>
              查看批准与回放
            </Link>
          </div>
        </header>

        <section className="evidence-summary" aria-labelledby="evidence-summary-heading">
          <div>
            <p className="eyebrow">先看结论</p>
            <h2 id="evidence-summary-heading">这页现在能告诉你什么</h2>
          </div>
          <div className="evidence-summary-metrics">
            <article><strong>{data.graph.nodes.length}</strong><span>个已校验版本化产物</span></article>
            <article><strong>{conclusionCount}</strong><span>个 Replication Finding</span></article>
            <article><strong>{unavailablePlaneCount}</strong><span>类证据仍有限制</span></article>
          </div>
          <p>
            图谱展示当前 Task / Run 中可验证的依赖关系。它不会自动证明素材权利、因果效果、商业批准或生产可用。
          </p>
        </section>

        <div className="evidence-layout">
          <main className="evidence-main">
            <section className="evidence-graph" aria-label="产物依赖图谱">
              <div className="evidence-section-heading">
                <div>
                  <p className="eyebrow">CANONICAL ARTIFACT GRAPH</p>
                  <h2>产物依赖图谱</h2>
                </div>
                <span>{data.graph.edges.length} 条依赖关系</span>
              </div>
              {data.graph.nodes.length > 0 ? (
                <div className="evidence-node-list">
                  {data.graph.nodes.map((node, index) => (
                    <article className={`evidence-node ${node.is_conclusion ? "evidence-node-conclusion" : ""}`} key={node.ref}>
                      <div className="evidence-node-index">{String(index + 1).padStart(2, "0")}</div>
                      <div className="evidence-node-body">
                        <header>
                          <div>
                            <small>{node.is_conclusion ? "复刻结论" : artifactStatusLabels[node.status]}</small>
                            <h3>{artifactLabels[node.artifact_type]} · v{node.version}</h3>
                          </div>
                          <div className="evidence-node-tags">
                            <span>{evidenceLevelLabels[node.evidence_level]}</span>
                            <span>{proofLevelLabels[node.proof_level]}</span>
                          </div>
                        </header>
                        <ArtifactDetails node={node} />
                      </div>
                    </article>
                  ))}
                </div>
              ) : (
                <div className="evidence-empty">
                  {graphLimitations.map((limitation) => <p key={limitation}>{limitation}</p>)}
                </div>
              )}
              {data.graph.edges.length > 0 && (
                <details className="evidence-edge-list">
                  <summary>查看依赖关系</summary>
                  <ol>
                    {data.graph.edges.map((edge) => {
                      const source = nodesByRef.get(edge.source_ref);
                      const target = nodesByRef.get(edge.target_ref);
                      return (
                        <li key={`${edge.kind}:${edge.source_ref}:${edge.target_ref}`}>
                          <strong>{source ? artifactLabels[source.artifact_type] : "外部版本引用"}</strong>
                          <span>→</span>
                          <strong>{target ? artifactLabels[target.artifact_type] : "外部版本引用"}</strong>
                          <small>{edge.verification_state === "verified" ? "运行时已验证" : "仅声明依赖"}</small>
                        </li>
                      );
                    })}
                  </ol>
                </details>
              )}
              {graphLimitations.length > 0 && data.graph.nodes.length > 0 && (
                <ul className="evidence-limitations">
                  {graphLimitations.map((limitation) => <li key={limitation}>{limitation}</li>)}
                </ul>
              )}
            </section>

            <section className="evidence-planes" aria-label="四类证据">
              <div className="evidence-section-heading">
                <div>
                  <p className="eyebrow">FOUR EVIDENCE PLANES</p>
                  <h2>四类证据分开看</h2>
                </div>
                <span>不合并成总分</span>
              </div>
              <div className="evidence-plane-grid">
                {data.evidence_planes.map((plane) => (
                  <EvidencePlane key={plane.kind} plane={plane} />
                ))}
              </div>
            </section>
          </main>

          <aside className="evidence-side" aria-label="证据边界">
            <section className="evidence-comparison">
              <p className="eyebrow">CONTROL / VARIANT</p>
              <h2>版本对比</h2>
              {canCompare && data.comparison.state === "available" ? (
                <>
                  <p>已绑定同一 Script 下的两个不可变版本。</p>
                  <Link
                    className="button button-primary"
                    to={`/scripts/${encodeURIComponent(data.comparison.script_ref)}/compare?control=${encodeURIComponent(data.comparison.control_version_ref)}&variant=${encodeURIComponent(data.comparison.variant_version_ref)}`}
                  >
                    打开 Control / Variant 对比
                  </Link>
                </>
              ) : (
                <>
                  <strong>当前不能打开对比</strong>
                  <p>当前没有同时绑定、可验证且属于同一 Script 的 Control / Variant 不可变版本。</p>
                  <details className="evidence-audit-details">
                    <summary>查看对比审计信息</summary>
                    <code>{data.comparison.public_code}</code>
                  </details>
                </>
              )}
            </section>

            <section className="evidence-read-only">
              <p className="eyebrow">READ-ONLY BOUNDARY</p>
              <h2>本页不会做什么</h2>
              <ul>
                {data.explicit_non_effects.map((nonEffect) => (
                  <li key={nonEffect}>{nonEffectLabels[nonEffect] ?? "不会执行未声明的写入或外部动作。"}</li>
                ))}
              </ul>
            </section>

            <section className="evidence-rule">
              <strong>判断规则</strong>
              <p>“不可用”“不适用”和“已隔离”是三种不同状态。它们都不是零，也不是失败分数。</p>
            </section>
          </aside>
        </div>
      </div>
    </section>
  );
}
