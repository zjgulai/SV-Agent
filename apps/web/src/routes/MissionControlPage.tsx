import { FormEvent, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";

import {
  api,
  type AgentCommandIntent,
  type MissionControlStageStatus,
} from "../api/client";
import "../features/sv-agent/styles/mission-control.css";

const runStateLabels: Record<string, string> = {
  draft: "草稿",
  planning: "正在规划",
  awaiting_input: "等待补充输入",
  runnable: "计划已就绪",
  running: "Agent 正在处理",
  awaiting_approval: "等待人工决定",
  blocked: "已阻断",
  completed_with_limits: "已完成，但有限制",
  failed: "技术执行失败",
  stopped: "已停止",
};

const stageStatusLabels: Record<MissionControlStageStatus, string> = {
  completed: "已完成",
  active: "当前",
  waiting: "等待上游",
  blocked: "已阻断",
  unknown: "尚无权威证明",
};

const intentLabels: Record<AgentCommandIntent, string> = {
  provide_input: "补充输入",
  request_plan: "请求计划",
  request_evidence: "请求证据",
  revise_plan: "修订计划",
  advance: "检查并推进",
  resume_recovery: "恢复原命令",
  stop: "停止 Run",
};

const intentEffects: Record<AgentCommandIntent, string> = {
  provide_input: "拟把说明作为当前 Task 的补充输入。",
  request_plan: "拟请求编译一份新的版本化 RunPlan。",
  request_evidence: "拟记录需要补齐的证据范围。",
  revise_plan: "拟请求新 RunPlan 版本，不覆盖历史版本。",
  advance: "拟重新检查前置条件并选择下一安全动作。",
  resume_recovery: "拟按原 command receipt 恢复，不创建第二次执行。",
  stop: "拟请求停止当前 Run，不代表删除 Task 或历史。",
};

const humanApprovalBoundary: Partial<Record<AgentCommandIntent, string>> = {
  request_evidence:
    "这不是 HumanApproval 的 request_evidence 决定，也不会关闭 ApprovalRequest。",
  stop: "这不是 HumanApproval 的 stop 决定，也不会关闭 ApprovalRequest。",
};

const nextActionCopy: Record<string, { label: string; reason: string }> = {
  FRONTIER_EVIDENCE_REQUIRED: {
    label: "刷新权威证据",
    reason: "当前前沿还不能由唯一、已验证的证据确定。",
  },
  PLAN_REQUEST_PREVIEW_ONLY: {
    label: "预览计划请求",
    reason: "当前只允许预览；本页不能创建 RunPlan 或启动 Run。",
  },
  INPUT_REQUIRED: {
    label: "预览补充输入",
    reason: "当前 Run 明确要求用户补充输入。",
  },
  PREREQUISITES_REQUIRE_RECHECK: {
    label: "预览下一安全动作",
    reason: "任何后续动作前都必须重新检查前置条件。",
  },
  RUN_ACTIVE: {
    label: "查看当前活动",
    reason: "当前 Run 正在处理；本页不能派发工作。",
  },
  HUMAN_APPROVAL_REQUIRED: {
    label: "查看待处理决定",
    reason: "HumanApproval 是独立边界，不能在 Mission Control 中代为决定。",
  },
  BLOCKER_RESOLUTION_REQUIRED: {
    label: "预览证据请求",
    reason: "必须先解决已记录的 blocker，不能靠猜测继续。",
  },
  COMPLETED_WITH_LIMITS: {
    label: "复核结果和限制",
    reason: "有限制完成不等于发布或 production acceptance。",
  },
  RECOVERY_RECEIPT_UNAVAILABLE: {
    label: "当前无法恢复",
    reason: "当前投影没有精确绑定、可验证的 command receipt。",
  },
  RUN_STOPPED: {
    label: "当前无可用动作",
    reason: "当前 Run 已停止。",
  },
};

const blockerCopy: Record<string, string> = {
  RUN_NOT_STARTED: "Task 已保存，但还没有权威 Run。",
  PLAN_FRONTIER_UNAVAILABLE:
    "当前 Run revision 缺少精确绑定的 RunPlan，不能把其他版本当作当前计划。",
  PLAN_FRONTIER_AMBIGUOUS:
    "RunPlan 前沿存在多个候选，必须先修复权威绑定。",
  ARTIFACT_FRONTIER_UNAVAILABLE:
    "当前 Run revision 缺少唯一且有效的 Artifact，不能从其他记录推断。",
  ARTIFACT_FRONTIER_AMBIGUOUS:
    "Artifact 前沿存在多个候选，必须先修复权威绑定。",
  ARTIFACT_FRONTIER_UNVERIFIED:
    "候选 Artifact 缺少权威 lineage 验证，不能作为当前产物。",
  APPROVAL_REQUIRED: "当前 Run 等待独立人工决定；Mission Control 不会代为决定。",
  APPROVAL_SET_TRUNCATED:
    "待决定记录超过本页安全读取上限，当前审批前沿保持未知。",
  APPROVAL_FRONTIER_INCONSISTENT:
    "待决定请求没有绑定到已验证的当前 Artifact，不能继续。",
  APPROVAL_STATE_INCONSISTENT:
    "Run 状态与待决定请求不一致，需要先检查权威记录。",
  REFERENCE_RIGHTS_BLOCKED: "当前参考素材的使用范围不允许继续推进。",
  INPUT_REQUIRED: "继续前需要你补充明确输入。",
  RUN_BLOCKED: "当前 Run 已被业务门禁阻断。",
  RUN_TECHNICAL_FAILURE: "当前 Run 出现技术失败，需要人工检查后再决定是否恢复。",
};

function localizedBlockerMessage(code: string) {
  return blockerCopy[code]
    ?? "记录到一项技术执行问题；请按稳定错误码检查，本页不会自动重试。";
}

function formatTime(value: string | null) {
  if (!value) return "尚未记录";
  return new Intl.DateTimeFormat("zh-CN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export function MissionControlPage() {
  const { taskId } = useParams<"taskId">();
  const workspace = useQuery({
    queryKey: ["sv-agent", "mission-control", taskId],
    queryFn: () => api.getSvAgentMissionControl(taskId!),
    enabled: Boolean(taskId),
  });
  const [intent, setIntent] = useState<AgentCommandIntent>("request_evidence");
  const [instruction, setInstruction] = useState("");
  const [preview, setPreview] = useState<{
    intent: AgentCommandIntent;
    instruction: string;
  } | null>(null);

  if (!taskId) {
    return <div className="page state-card state-error" role="alert">Task 标识缺失。</div>;
  }
  if (workspace.isPending) {
    return <div className="page state-card">正在读取 Mission Control…</div>;
  }
  if (workspace.isError || !workspace.data) {
    return (
      <section className="page">
        <Link className="back-link" to="/sv-agent/tasks">← 返回 Task 收件箱</Link>
        <div className="state-card state-error" role="alert">
          <h1>无法打开 Mission Control</h1>
          <p>权威状态读取失败。没有 Task、Run 或审批被修改。</p>
          <button className="button button-secondary" onClick={() => workspace.refetch()} type="button">
            重新读取
          </button>
        </div>
      </section>
    );
  }

  const data = workspace.data;
  const completedStageCount = data.stages.filter(
    (stage) => stage.status === "completed",
  ).length;
  const unknownStageCount = data.stages.filter(
    (stage) => stage.status === "unknown",
  ).length;
  const blockerCodes = new Set(data.blockers.map((blocker) => blocker.code));
  const planMissingMessage = blockerCodes.has("PLAN_FRONTIER_AMBIGUOUS")
    ? "RunPlan 前沿不唯一，界面不会选择任意最新记录。"
    : blockerCodes.has("PLAN_FRONTIER_UNAVAILABLE")
      ? "当前 Run revision 没有精确绑定的 RunPlan；计划保持未知。"
      : "当前没有已持久化 RunPlan；界面不会根据对话猜测计划。";
  const artifactMissingMessage = !data.run
    ? "尚未开始 Run，因此没有当前 Artifact。"
    : blockerCodes.has("ARTIFACT_FRONTIER_AMBIGUOUS")
      ? "Artifact 前沿不唯一，界面不会选择任意最新记录。"
      : blockerCodes.has("ARTIFACT_FRONTIER_UNVERIFIED")
        ? "发现候选 Artifact，但没有权威 lineage 验证；当前产物保持未知。"
        : blockerCodes.has("ARTIFACT_FRONTIER_UNAVAILABLE")
          ? "当前 Run revision 没有唯一且有效的 Artifact；当前产物保持未知。"
          : "当前没有权威 current Artifact；界面不会从最新记录推断。";
  const explanationSummary = /[\u3400-\u9fff]/u.test(data.explanation.summary)
    ? data.explanation.summary
    : !data.run
      ? "Task 已保存，但还没有权威 Run。"
      : data.current_artifact
        ? `当前 Run 状态为${runStateLabels[data.run.state] ?? data.run.state}；唯一验证的当前产物为 ${data.current_artifact.artifact_type} v${data.current_artifact.version}。`
        : `当前 Run 状态为${runStateLabels[data.run.state] ?? data.run.state}；${artifactMissingMessage}`;
  const recoveryAvailable =
    data.next_safe_action.interaction_intent === "resume_recovery";
  const localizedNextAction = nextActionCopy[data.next_safe_action.reason_code] ?? {
    label: data.next_safe_action.label,
    reason: data.next_safe_action.reason,
  };
  const currentStage = data.stages.find(
    (stage) => stage.key === data.current_stage,
  );
  const submitPreview = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const normalized = instruction.trim();
    if (!normalized) return;
    setPreview({ intent, instruction: normalized });
  };

  return (
    <section className="mission-control-page">
      <div className="mission-control-frame">
        <header className="mission-control-hero">
          <div>
            <Link className="back-link" to="/sv-agent/tasks">← 返回 Task 收件箱</Link>
            <p className="eyebrow">SV-AGENT · MISSION CONTROL</p>
            <h1>{data.task.subject}</h1>
            <p>{data.task.decision_question}</p>
          </div>
          <div className="mission-control-authority">
            <strong>PostgreSQL 权威状态</strong>
            <span>Task revision {data.task.task_revision}</span>
            <span>{data.run ? `Run · ${runStateLabels[data.run.state] ?? data.run.state}` : "尚未创建 Run"}</span>
          </div>
        </header>

        <div className="mission-control-grid">
          <main className="mission-control-main">
            <section className="mission-agent-explanation" aria-labelledby="agent-explanation-heading">
              <p className="eyebrow">AGENT EXPLANATION</p>
              <h2 id="agent-explanation-heading">SV-Agent 当前判断</h2>
              <p>{explanationSummary}</p>
              {data.explanation.citations.length > 0 ? (
                <details className="mission-audit-details">
                  <summary>查看引用审计信息</summary>
                  <div className="mission-citations" aria-label="解释引用">
                    {data.explanation.citations.map((citation) => (
                      <code key={`${citation.kind}:${citation.ref}`}>{citation.ref}</code>
                    ))}
                  </div>
                </details>
              ) : (
                <p className="mission-missing">暂无 Artifact 或 Evidence 引用，因此不生成额外结论。</p>
              )}
            </section>

            <section className="mission-path" aria-label="七步复刻路径">
              <div className="mission-section-heading">
                <div>
                  <p className="eyebrow">7-STAGE PATH</p>
                  <h2>本次复刻怎么推进</h2>
                </div>
                <span>已证实完成 {completedStageCount} · 未知 {unknownStageCount}</span>
              </div>
              <ol>
                {data.stages.map((stage, index) => (
                  <li className={`mission-stage mission-stage-${stage.status}`} key={stage.key}>
                    <span>{stage.status === "completed" ? "✓" : index + 1}</span>
                    <div>
                      <strong>{stage.label}</strong>
                      <small>{stageStatusLabels[stage.status]}</small>
                    </div>
                  </li>
                ))}
              </ol>
            </section>

            <section className="mission-plan" aria-labelledby="current-plan-heading">
              <div className="mission-section-heading">
                <div>
                  <p className="eyebrow">CURRENT PLAN</p>
                  <h2 id="current-plan-heading">当前 RunPlan</h2>
                </div>
                {data.plan && <span>v{data.plan.version} · {data.plan.workflow_version}</span>}
              </div>
              {data.plan ? (
                <>
                  <p>{data.plan.workflow_name}</p>
                  <div className="mission-plan-steps">
                    {data.plan.steps.map((step) => (
                      <article key={step.step_id}>
                        <span>{step.order}</span>
                        <div><strong>{step.capability_name}</strong><small>{step.execution_mode}</small></div>
                      </article>
                    ))}
                  </div>
                  <ul className="mission-limitations">
                    {data.plan.limitations.map((limitation) => <li key={limitation}>{limitation}</li>)}
                  </ul>
                </>
              ) : (
                <div className="mission-empty">{planMissingMessage}</div>
              )}
            </section>

            <section className="mission-activity" aria-labelledby="agent-activity-heading">
              <div className="mission-section-heading">
                <div>
                  <p className="eyebrow">AGENT ACTIVITY</p>
                  <h2 id="agent-activity-heading">ToolRuns</h2>
                </div>
                <span>只显示当前权威记录</span>
              </div>
              {data.tool_runs_truncated && (
                <p className="mission-truncated" role="status">
                  这里只显示最近 20 条 ToolRun；更早记录未在本页展开。
                </p>
              )}
              {data.tool_runs.length > 0 ? data.tool_runs.map((toolRun) => (
                <article key={toolRun.ref}>
                  <div><strong>{toolRun.tool_name}</strong><span>{toolRun.status}</span></div>
                  <p>{toolRun.intent_summary}</p>
                  <small>{formatTime(toolRun.finished_at ?? toolRun.started_at)}</small>
                  {toolRun.stable_error_code && <code>{toolRun.stable_error_code}</code>}
                </article>
              )) : <div className="mission-empty">当前 Run 没有 ToolRun 记录。</div>}
            </section>

            <section className="mission-command" aria-labelledby="command-preview-heading">
              <div className="mission-section-heading">
                <div>
                  <p className="eyebrow">CONVERSATIONAL COMMAND PREVIEW</p>
                  <h2 id="command-preview-heading">先看 AgentCommand，再决定是否继续</h2>
                </div>
                <span>浏览器预览 · 不提交</span>
              </div>
              <form onSubmit={submitPreview}>
                <label htmlFor="command-intent">命令意图</label>
                <select id="command-intent" value={intent} onChange={(event) => setIntent(event.target.value as AgentCommandIntent)}>
                  {Object.entries(intentLabels).map(([value, label]) => (
                    <option
                      disabled={value === "resume_recovery" && !recoveryAvailable}
                      key={value}
                      value={value}
                    >
                      {label}
                    </option>
                  ))}
                </select>
                {!recoveryAvailable && (
                  <p className="mission-command-note">
                    当前投影没有可恢复的 command receipt；resume_recovery 不可用。
                  </p>
                )}
                <label htmlFor="command-instruction">给 SV-Agent 的说明</label>
                <textarea id="command-instruction" maxLength={1000} required rows={3} value={instruction} onChange={(event) => setInstruction(event.target.value)} />
                <button className="button button-primary" type="submit">预览 AgentCommand</button>
              </form>
              {preview && (
                <div className="mission-command-preview" role="region" aria-label="AgentCommand 预览">
                  <strong>{preview.intent}</strong>
                  <span>Task revision {data.task.task_revision}</span>
                  {data.run && <span>Run revision {data.run.run_revision}</span>}
                  <p>{preview.instruction}</p>
                  <p>
                    <strong>预期 effect：</strong>
                    {preview.intent === "resume_recovery" && !recoveryAvailable
                      ? "不会形成恢复动作；当前缺少可验证的 command receipt。"
                      : intentEffects[preview.intent]}
                  </p>
                  <p><strong>明确 non-effect：</strong>只会形成命令预览，不会提交或执行。</p>
                  <p><strong>所需人工门：</strong>未来若开放写入，仍需服务端授权；本页不会创建 HumanApproval 决定。</p>
                  {humanApprovalBoundary[preview.intent] && (
                    <p>{humanApprovalBoundary[preview.intent]}</p>
                  )}
                  {preview.intent === "resume_recovery" && !recoveryAvailable && (
                    <p className="mission-command-unavailable">
                      当前投影没有可恢复的 command receipt；resume_recovery 不可用。
                    </p>
                  )}
                </div>
              )}
            </section>
          </main>

          <aside className="mission-control-side" aria-label="本次复刻包">
            <section>
              <p className="eyebrow">CURRENT BUNDLE</p>
              <h2>本次复刻包</h2>
              <dl>
                <div><dt>目标</dt><dd>{data.task.goal_track === "product_replication" ? "产品复刻" : "品牌声量"}</dd></div>
                <div><dt>平台</dt><dd>{data.task.platform} · {data.task.market}</dd></div>
                <div><dt>主机制</dt><dd>{data.run?.primary_mechanism ?? "尚未选择"}</dd></div>
                <div>
                  <dt>当前阶段</dt>
                  <dd>
                    {currentStage
                      ? `${currentStage.label} · ${stageStatusLabels[currentStage.status]}`
                      : "未知"}
                  </dd>
                </div>
              </dl>
              <Link
                className="button button-secondary mission-evidence-link"
                to={`/sv-agent/tasks/${encodeURIComponent(data.task.task_id)}/evidence`}
              >
                查看证据与产物
              </Link>
              <Link
                className="button button-secondary mission-evidence-link"
                to={`/sv-agent/tasks/${encodeURIComponent(data.task.task_id)}/approval-replay`}
              >
                查看批准与回放
              </Link>
            </section>

            <section aria-labelledby="current-artifact-heading">
              <h2 id="current-artifact-heading">当前产物</h2>
              {data.current_artifact ? (
                <article className="mission-artifact">
                  <small>{data.current_artifact.status}</small>
                  <strong>{data.current_artifact.artifact_type} · v{data.current_artifact.version}</strong>
                  <span>{data.current_artifact.evidence_level} evidence · {data.current_artifact.proof_level} proof</span>
                  <details className="mission-audit-details">
                    <summary>查看产物审计信息</summary>
                    <code>{data.current_artifact.ref}</code>
                  </details>
                </article>
              ) : <div className="mission-empty">{artifactMissingMessage}</div>}
            </section>

            <section aria-labelledby="blockers-heading">
              <h2 id="blockers-heading">阻塞与下一步</h2>
              {data.blockers.length > 0 ? data.blockers.map((blocker) => (
                <article className="mission-blocker" key={`${blocker.code}:${blocker.source_ref}`}>
                  <code>{blocker.code}</code>
                  <p>{localizedBlockerMessage(blocker.code)}</p>
                  <details className="mission-audit-details">
                    <summary>查看阻塞来源</summary>
                    <small>{blocker.source_ref}</small>
                  </details>
                </article>
              )) : <p className="mission-clear">当前没有已记录 blocker。</p>}
              <article className="mission-next-action">
                <small>NEXT SAFE ACTION</small>
                <strong>{localizedNextAction.label}</strong>
                <p>{localizedNextAction.reason}</p>
                <span>当前仅展示，不可执行</span>
                <details className="mission-audit-details">
                  <summary>查看下一步审计信息</summary>
                  <code>{data.next_safe_action.reason_code}</code>
                  {data.next_safe_action.basis_refs.map((ref) => (
                    <small key={ref}>{ref}</small>
                  ))}
                </details>
              </article>
            </section>

            <section className="mission-guard">
              <strong>SV-Agent 不会做什么</strong>
              <p>不会把播放量变成产品事实，不会展示私有推理，也不会绕过人工门进行生成、渲染或发布。</p>
            </section>
          </aside>
        </div>
      </div>
    </section>
  );
}
