import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";

import {
  api,
  type ApprovalDecision,
  type ApprovalReplayProjection,
  type EvidenceArtifactType,
  type ReplayTimelineKind,
} from "../api/client";
import "../features/sv-agent/styles/approval-replay.css";

const artifactLabels: Record<EvidenceArtifactType, string> = {
  reference_bundle: "参考素材包",
  decomposition_map: "内容拆解图",
  pattern_hypothesis: "爆款机制假设",
  replication_plan: "复刻计划",
  fact_map: "事实绑定图",
  replication_contract: "复刻合同",
  adaptation_package: "品牌适配包",
  media_integrity_record: "媒体完整性记录",
  replication_finding: "复刻结论",
};

const decisionLabels: Record<ApprovalDecision, string> = {
  approve: "批准",
  reject: "拒绝",
  request_evidence: "请求补充证据",
  stop: "停止",
};

const timelineLabels: Record<ReplayTimelineKind, string> = {
  task_event: "Task 状态",
  plan_revision: "RunPlan",
  artifact_revision: "版本化产物",
  approval_request: "批准请求",
  tool_run: "ToolRun",
  decision: "人工决定",
};

const nonEffectLabels: Record<string, string> = {
  does_not_write_postgresql: "不会写入 PostgreSQL。",
  does_not_decide_approvals: "不会代替人工作出批准决定。",
  does_not_advance_task_or_run: "不会推进 Task 或 Run。",
  does_not_call_providers: "不会调用模型或其他供应商。",
  does_not_render_or_publish: "不会生成、渲染或发布视频。",
};

function ListBlock({
  title,
  items,
  empty,
}: {
  title: string;
  items: string[];
  empty: string;
}) {
  return (
    <div className="approval-list-block">
      <h4>{title}</h4>
      {items.length > 0 ? (
        <ul>{items.map((item, index) => <li key={`${item}:${index}`}>{item}</li>)}</ul>
      ) : (
        <p>{empty}</p>
      )}
    </div>
  );
}

function ApprovalCard({
  approval,
}: {
  approval: ApprovalReplayProjection["approvals"][number];
}) {
  const artifactLabel = artifactLabels[approval.target_artifact_type];
  const stateLabel = approval.decision_state === "pending"
    ? "等待人工决定"
    : approval.decision
      ? decisionLabels[approval.decision]
      : "已记录决定";

  return (
    <article
      className={`approval-card approval-card-${approval.scope_state}`}
      aria-label={`${artifactLabel} v${approval.target_version}`}
    >
      <header>
        <div>
          <p className="eyebrow">{approval.gate_kind}</p>
          <h3>{artifactLabel} · v{approval.target_version}</h3>
        </div>
        <div className="approval-card-state">
          <strong>{stateLabel}</strong>
          {approval.scope_state === "stale" && (
            <span>已失效，仅保留历史事实</span>
          )}
        </div>
      </header>

      <div className="approval-card-grid">
        <ListBlock
          title="如果决定通过，会发生什么"
          items={approval.predicted_effects}
          empty="没有声明后续效果。"
        />
        <ListBlock
          title="无论如何都不会发生什么"
          items={approval.explicit_non_effects}
          empty="没有额外声明。"
        />
        <ListBlock title="判断依据" items={approval.evidence} empty="没有可展示的依据。" />
        <ListBlock title="已知限制" items={approval.limitations} empty="没有额外限制。" />
        <ListBlock
          title="何时失效"
          items={approval.stale_conditions}
          empty="没有声明失效条件。"
        />
      </div>

      <details className="approval-binding-details">
        <summary>查看版本绑定</summary>
        <dl>
          <div><dt>请求版本</dt><dd>v{approval.request_version}</dd></div>
          <div><dt>Task revision</dt><dd>{approval.audit.task_revision}</dd></div>
          <div><dt>Run revision</dt><dd>{approval.audit.run_revision}</dd></div>
        </dl>
      </details>
    </article>
  );
}

export function ApprovalReplayPage() {
  const { taskId } = useParams<"taskId">();
  const workspace = useQuery({
    queryKey: ["sv-agent", "approval-replay", taskId],
    queryFn: () => api.getSvAgentApprovalReplay(taskId!),
    enabled: Boolean(taskId),
  });

  if (!taskId) {
    return <div className="page state-card state-error" role="alert">Task 标识缺失。</div>;
  }
  if (workspace.isPending) {
    return <div className="page state-card">正在读取批准与回放…</div>;
  }
  if (workspace.isError || !workspace.data) {
    return (
      <section className="page">
        <Link className="back-link" to={`/sv-agent/tasks/${encodeURIComponent(taskId)}`}>
          ← 返回 Mission Control
        </Link>
        <div className="state-card state-error" role="alert">
          <h1>无法读取批准与回放</h1>
          <p>没有批准、Task、Run 或产物被修改。</p>
          <button className="button button-secondary" onClick={() => workspace.refetch()} type="button">
            重新读取
          </button>
        </div>
      </section>
    );
  }

  const data = workspace.data;

  return (
    <section className="approval-page">
      <div className="approval-frame">
        <header className="approval-hero">
          <div>
            <Link className="back-link" to={`/sv-agent/tasks/${encodeURIComponent(taskId)}`}>
              ← 返回 Mission Control
            </Link>
            <p className="eyebrow">SV-AGENT · APPROVAL &amp; REPLAY</p>
            <h1>{data.task.subject}的批准与回放</h1>
            <p>先判断批准请求是否仍然有效，再按同一事件截止点回看发生过什么。</p>
          </div>
          <div className="approval-authority">
            <strong>PostgreSQL 权威投影</strong>
            <span>Task revision {data.task.task_revision}</span>
            <span>{data.run ? `Run revision ${data.run.run_revision}` : "尚未创建 Run"}</span>
          </div>
        </header>

        <section className="approval-summary" aria-labelledby="approval-summary-heading">
          <div>
            <p className="eyebrow">先看结论</p>
            <h2 id="approval-summary-heading">现在需要关注什么</h2>
          </div>
          <div className="approval-summary-metrics">
            <article><strong>{data.summary.pending} 个待决定</strong></article>
            <article><strong>{data.summary.decided} 个已记录决定</strong></article>
            <article><strong>{data.summary.stale} 个已失效范围</strong></article>
          </div>
          <p>本页不会提交任何人工决定。</p>
        </section>

        <div className="approval-layout">
          <main className="approval-main">
            <section className="approval-requests" aria-label="批准请求">
              <div className="approval-section-heading">
                <div>
                  <p className="eyebrow">VERSION-BOUND REQUESTS</p>
                  <h2>批准请求</h2>
                </div>
                <span>决定词汇：{data.decision_vocabulary.map((item) => decisionLabels[item]).join(" / ")}</span>
              </div>

              {data.approvals_truncated && (
                <p className="approval-notice" role="status">只显示当前安全上限内的批准请求。</p>
              )}
              {data.approvals.length > 0 ? (
                <div className="approval-card-list">
                  {data.approvals.map((approval, index) => (
                    <ApprovalCard
                      approval={approval}
                      key={`${approval.gate_kind}:${approval.target_artifact_type}:${approval.target_version}:${approval.request_version}:${index}`}
                    />
                  ))}
                </div>
              ) : (
                <div className="approval-empty">当前没有已记录的批准请求。</div>
              )}
            </section>

            <section className="approval-timeline" aria-label="事实回放">
              <div className="approval-section-heading">
                <div>
                  <p className="eyebrow">FACTUAL REPLAY</p>
                  <h2>事实回放</h2>
                </div>
                <span>截至事件序号 {data.timeline.snapshot_through_sequence}</span>
              </div>
              {data.timeline.truncated && (
                <p className="approval-notice" role="status">
                  当前只显示安全上限内的回放；此页面暂不提供继续分页。
                </p>
              )}
              {data.timeline.entries.length > 0 ? (
                <ol>
                  {data.timeline.entries.map((entry) => (
                    <li key={entry.event_sequence}>
                      <span className="approval-timeline-marker" aria-hidden="true" />
                      <article>
                        <small>{timelineLabels[entry.kind]}</small>
                        <p>{entry.summary}</p>
                        <details className="approval-audit-details">
                          <summary>查看安全审计信息</summary>
                          <div>事件序号 {entry.event_sequence}</div>
                          <div>事件类型 {entry.event_type}</div>
                          <div>Task revision {entry.task_revision}</div>
                          {entry.run_revision !== null && (
                            <div>Run revision {entry.run_revision}</div>
                          )}
                        </details>
                      </article>
                    </li>
                  ))}
                </ol>
              ) : (
                <div className="approval-empty">当前权威快照没有可回放事件。</div>
              )}
            </section>
          </main>

          <aside className="approval-side" aria-label="回放边界">
            <section>
              <p className="eyebrow">READ-ONLY BOUNDARY</p>
              <h2>这一页不会做什么</h2>
              <ul>
                {data.explicit_non_effects.map((item) => (
                  <li key={item}>{nonEffectLabels[item] ?? "不会执行未声明的写入或外部动作。"}</li>
                ))}
              </ul>
            </section>
            <section>
              <p className="eyebrow">NEXT VIEW</p>
              <h2>继续核对依据</h2>
              <p>如果要判断一项请求是否合理，先回到证据与产物页核对版本和证据边界。</p>
              <Link
                className="button button-secondary"
                to={`/sv-agent/tasks/${encodeURIComponent(taskId)}/evidence`}
              >
                查看证据与产物
              </Link>
            </section>
          </aside>
        </div>
      </div>
    </section>
  );
}
