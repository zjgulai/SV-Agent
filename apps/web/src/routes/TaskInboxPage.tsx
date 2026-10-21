import { useQuery } from "@tanstack/react-query";
import { Link, useLocation } from "react-router-dom";

import type {
  TaskInboxLane,
  TaskInboxOrderingReason,
} from "../api/client";
import { api } from "../api/client";
import { readBrowserTaskDraftsFrom } from "../features/sv-agent/browserTaskDrafts";
import { readBrowserNewTaskDraftsFrom } from "../features/sv-agent/browserNewTaskDrafts";
import "../features/sv-agent/task-inbox.css";

const laneLabels: Record<TaskInboxLane, string> = {
  needs_decision: "等待你的决定",
  needs_input: "等待补充信息",
  blocked: "存在业务阻断",
  technical_attention: "需要技术检查",
  agent_running: "Agent 正在处理",
  completed_with_limits: "已完成，但有限制",
  stopped: "已停止",
  not_started: "尚未开始 Run",
};

const orderingReasons: Record<TaskInboxOrderingReason, string> = {
  human_decision_required: "当前有人类决定待处理",
  user_input_required: "继续前需要补充输入",
  business_blocker_present: "当前业务门禁阻止继续",
  runtime_integrity_attention: "运行状态与决定记录不一致",
  technical_failure_requires_review: "技术执行失败，需要人工检查",
  agent_work_in_progress: "当前 Run 正在执行或准备执行",
  completed_with_declared_limits: "结果已形成，但必须保留限制",
  stopped_by_decision: "Task 已被明确停止",
  run_not_started: "Task 已保存，但还没有 active Run",
};

function formatTime(value: string) {
  return new Intl.DateTimeFormat("zh-CN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export function TaskInboxPage() {
  const location = useLocation();
  const inbox = useQuery({
    queryKey: ["sv-agent", "task-inbox"],
    queryFn: api.listSvAgentTasks,
  });
  const localDrafts = readBrowserTaskDraftsFrom(() =>
    typeof window === "undefined" ? null : window.sessionStorage,
  );
  const newTaskDrafts = readBrowserNewTaskDraftsFrom(() =>
    typeof window === "undefined" ? null : window.sessionStorage,
  );
  const localDraftInvalid =
    localDrafts.invalidDraftIgnored || newTaskDrafts.invalidDraftIgnored;

  return (
    <section className="page page-wide task-inbox-page">
      <div className="page-heading">
        <div className="task-inbox-intro">
          <p className="eyebrow">SV-AGENT · READ-ONLY NATIVE SHELL</p>
          <h1>Task 与决定收件箱</h1>
          <p>先看哪里需要你决定、哪里正在推进、哪里被证据或运行边界挡住。</p>
        </div>
        <Link className="button button-primary" to="/sv-agent/tasks/new">新建本地草稿</Link>
      </div>

      {(location.state as { localDraftSaved?: boolean } | null)?.localDraftSaved && (
        <div className="state-card" role="status" aria-live="polite">
          草稿已保存到当前标签页；尚未写入 PostgreSQL，也没有启动 Agent。
        </div>
      )}

      <div className="task-inbox-authority" aria-label="数据边界">
        <span><strong>已保存状态：</strong> PostgreSQL</span>
        <span><strong>服务器能力：</strong> 只读查看</span>
        <span><strong>不会执行：</strong> 生成、渲染或发布</span>
      </div>

      <section className="task-inbox-section" aria-labelledby="persisted-task-heading">
        <div className="task-inbox-section-heading">
          <div>
            <h2 id="persisted-task-heading">已保存的 Task</h2>
            <p>这里仅显示服务器已保存的 Task 和 active Run，不使用浏览器草稿冒充运行状态。</p>
          </div>
          <span>PostgreSQL 权威记录</span>
        </div>

        {inbox.isPending && <div className="state-card">正在读取 Task…</div>}
        {inbox.isError && (
          <div className="state-card state-error" role="alert">
            Task 读取失败。数据库中的记录没有被修改，请稍后重试。
          </div>
        )}
        {inbox.data?.items.length === 0 && (
          <div className="empty-state compact">
            <h2>还没有已保存的 Task</h2>
            <p>你可以保存浏览器本地草稿；本页不会偷偷创建或启动服务器 Task。</p>
          </div>
        )}
        {inbox.data?.truncated && (
          <div className="state-card" role="status">
            当前按待处理类型和最近更新时间显示前 100 个 Task。
          </div>
        )}
        <div className="task-inbox-list">
          {inbox.data?.items.map((item) => (
            <article className="task-inbox-card" key={item.task_id}>
              <div>
                <div className="task-inbox-card-meta">
                  <span>{item.goal_track === "product_replication" ? "产品复刻" : "品牌声量"}</span>
                  <span>Task revision {item.task_revision}</span>
                  {item.run_state && <span>Run · {item.run_state}</span>}
                </div>
                <h3>{item.subject}</h3>
                <p>{item.decision_question}</p>
              </div>
              <div className="task-inbox-order">
                <strong>{laneLabels[item.lane]}</strong>
                <p>排序原因：{orderingReasons[item.ordering_reason]}</p>
                {item.pending_decision_count > 0 && (
                  <p>{item.pending_decision_count} 个当前决定待处理</p>
                )}
                <time dateTime={item.priority_at}>{formatTime(item.priority_at)}</time>
                <Link to={`/sv-agent/tasks/${encodeURIComponent(item.task_id)}`}>
                  打开 Mission Control
                </Link>
              </div>
            </article>
          ))}
        </div>
      </section>

      <section className="task-inbox-section" aria-labelledby="browser-draft-heading">
        <div className="task-inbox-section-heading">
          <div>
            <h2 id="browser-draft-heading">浏览器本地草稿</h2>
            <p>草稿只保存在当前浏览器，不在 PostgreSQL 中，也没有运行中的 Agent。</p>
          </div>
          <span>非权威 · 本机</span>
        </div>
        {localDraftInvalid && (
          <div className="state-card" role="status">
            已忽略无法安全读取的本地草稿；服务器 Task 不受影响。
          </div>
        )}
        {localDrafts.drafts.length === 0 && newTaskDrafts.drafts.length === 0 ? (
          <div className="task-inbox-local">
            <p>当前没有可显示的本地草稿。</p>
          </div>
        ) : (
          <div className="task-inbox-draft-list">
            {newTaskDrafts.drafts.map((draft) => (
              <article className="task-inbox-draft" key={draft.draft_id}>
                <small>尚未写入 PostgreSQL</small>
                <h3>{draft.subject}</h3>
                <p>{draft.decision_question}</p>
                <span>{draft.goal_track === "product_replication" ? "产品复刻" : "品牌声量"} · {draft.platform} · {draft.market}</span>
                <time dateTime={draft.updated_at}>{formatTime(draft.updated_at)}</time>
                <Link to={`/sv-agent/tasks/new?draft=${encodeURIComponent(draft.draft_id)}`}>
                  继续编辑
                </Link>
              </article>
            ))}
            {localDrafts.drafts.map((draft) => (
              <article className="task-inbox-draft" key={draft.draft_id}>
                <small>尚未写入 PostgreSQL</small>
                <h3>{draft.subject}</h3>
                <p>{draft.decision_question}</p>
                <time dateTime={draft.updated_at}>{formatTime(draft.updated_at)}</time>
              </article>
            ))}
          </div>
        )}
      </section>
    </section>
  );
}

