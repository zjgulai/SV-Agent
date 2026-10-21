import { FormEvent, useMemo, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";

import {
  readBrowserNewTaskDraftsFrom,
  saveBrowserNewTaskDraft,
  type DraftChildSafetyState,
  type DraftClaimScope,
  type DraftGoalTrack,
  type DraftPlatform,
  type DraftRightsState,
} from "../features/sv-agent/state/browserNewTaskDrafts";
import "../features/sv-agent/styles/new-task.css";

const defaultStopCondition = "权利或儿童安全边界不闭合时停止";

function getSessionStorage() {
  return typeof window === "undefined" ? null : window.sessionStorage;
}

function isPublicHttpReference(value: string) {
  try {
    const parsed = new URL(value.trim());
    return (
      (parsed.protocol === "https:" || parsed.protocol === "http:") &&
      !parsed.username &&
      !parsed.password
    );
  } catch {
    return false;
  }
}

export function NewTaskPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const requestedDraftId = searchParams.get("draft");
  const initialDraft = useMemo(() => {
    if (!requestedDraftId) return null;
    return (
      readBrowserNewTaskDraftsFrom(getSessionStorage).drafts.find(
        (draft) => draft.draft_id === requestedDraftId,
      ) ?? null
    );
  }, [requestedDraftId]);
  const [goalTrack, setGoalTrack] = useState<DraftGoalTrack>(
    initialDraft?.goal_track ?? "brand_voice_social_resonance",
  );
  const [claimScope, setClaimScope] = useState<DraftClaimScope>(
    initialDraft?.claim_scope ?? "no_product_claims",
  );
  const [subject, setSubject] = useState(initialDraft?.subject ?? "");
  const [decisionQuestion, setDecisionQuestion] = useState(
    initialDraft?.decision_question ?? "",
  );
  const [referenceUrl, setReferenceUrl] = useState(
    initialDraft?.reference_url ?? "",
  );
  const [platform, setPlatform] = useState<DraftPlatform>(
    initialDraft?.platform ?? "tiktok",
  );
  const [market, setMarket] = useState(initialDraft?.market ?? "US");
  const [language, setLanguage] = useState(initialDraft?.language ?? "en-US");
  const [windowStart, setWindowStart] = useState(
    initialDraft?.performance_window.start ?? "",
  );
  const [windowEnd, setWindowEnd] = useState(
    initialDraft?.performance_window.end ?? "",
  );
  const [timezone, setTimezone] = useState(
    initialDraft?.performance_window.timezone ?? "UTC",
  );
  const [stopCondition, setStopCondition] = useState(
    initialDraft?.stop_condition ?? defaultStopCondition,
  );
  const [productSnapshotId, setProductSnapshotId] = useState(
    initialDraft?.product_snapshot_id ?? "",
  );
  const [rightsState, setRightsState] = useState<DraftRightsState>(
    initialDraft?.initial_rights_state ?? "unknown",
  );
  const [childSafetyState, setChildSafetyState] =
    useState<DraftChildSafetyState>(
      initialDraft?.initial_child_safety_state ?? "review_required",
    );
  const [rightsAcknowledged, setRightsAcknowledged] = useState(
    initialDraft?.boundary_acknowledgements.rights_requires_separate_human_gate ??
      false,
  );
  const [childSafetyAcknowledged, setChildSafetyAcknowledged] = useState(
    initialDraft?.boundary_acknowledgements
      .child_safety_requires_separate_human_gate ?? false,
  );
  const [error, setError] = useState<string | null>(null);
  const [invalidField, setInvalidField] = useState<string | null>(null);

  function invalidFieldProps(fieldId: string) {
    return invalidField === fieldId
      ? { "aria-describedby": "new-task-error", "aria-invalid": true as const }
      : {};
  }

  function selectGoal(next: DraftGoalTrack) {
    setGoalTrack(next);
    if (next === "product_replication") {
      setClaimScope("product_claims");
    } else {
      setClaimScope("no_product_claims");
      setProductSnapshotId("");
    }
  }

  function selectClaimScope(next: DraftClaimScope) {
    setClaimScope(next);
    if (next === "no_product_claims") setProductSnapshotId("");
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setInvalidField(null);
    const firstInvalidField =
      !subject.trim()
        ? "task-subject"
        : !decisionQuestion.trim()
          ? "task-question"
          : !isPublicHttpReference(referenceUrl)
            ? "task-reference"
            : !/^[A-Z]{2}$/.test(market.trim().toUpperCase())
              ? "task-market"
              : !language.trim()
                ? "task-language"
                : !windowStart
                  ? "window-start"
                  : !windowEnd || windowEnd < windowStart
                    ? "window-end"
                    : !timezone.trim()
                      ? "task-timezone"
                      : !stopCondition.trim()
                        ? "task-stop-condition"
                        : claimScope === "product_claims" && !productSnapshotId.trim()
                          ? "product-snapshot-id"
                          : null;
    if (firstInvalidField) {
      setInvalidField(firstInvalidField);
      setError("请检查公开链接、市场代码、观察窗口和标记字段后再保存。");
      queueMicrotask(() => document.getElementById(firstInvalidField)?.focus());
      return;
    }
    const now = new Date().toISOString();
    const result = saveBrowserNewTaskDraft(
      (() => {
        try {
          return getSessionStorage();
        } catch {
          return null;
        }
      })(),
      {
        draft_id: initialDraft?.draft_id ?? globalThis.crypto.randomUUID(),
        created_at: initialDraft?.created_at ?? now,
        updated_at: now,
        goal_track: goalTrack,
        decision_question: decisionQuestion.trim(),
        reference_url: referenceUrl.trim(),
        subject: subject.trim(),
        platform,
        market: market.trim().toUpperCase(),
        language: language.trim(),
        performance_window: {
          start: windowStart,
          end: windowEnd,
          timezone: timezone.trim(),
        },
        stop_condition: stopCondition.trim(),
        claim_scope: claimScope,
        product_snapshot_id:
          claimScope === "product_claims" ? productSnapshotId.trim() || null : null,
        initial_rights_state: rightsState,
        initial_child_safety_state: childSafetyState,
        boundary_acknowledgements: {
          rights_requires_separate_human_gate: rightsAcknowledged,
          child_safety_requires_separate_human_gate: childSafetyAcknowledged,
        },
      },
    );
    if (!result.ok) {
      setError(
        result.reason === "invalid_draft"
          ? "请检查公开链接、市场代码、观察窗口和边界确认后再保存。"
          : result.reason === "storage_limit"
            ? "本地草稿空间已满，草稿未保存。你填写的内容仍留在本页。"
            : "浏览器阻止本地存储，草稿未保存。你填写的内容仍留在本页。",
      );
      return;
    }
    navigate("/sv-agent/tasks", { state: { localDraftSaved: true } });
  }

  return (
    <section className="page page-wide new-task-page">
      <Link className="back-link" to="/sv-agent/tasks">← 返回 Task 收件箱</Link>
      <div className="new-task-heading">
        <div>
          <p className="eyebrow">SV-AGENT · BROWSER-LOCAL BRIEF</p>
          <h1>新建复刻任务草稿</h1>
          <p className="lede">
            保存只写入当前浏览器标签页，不会创建服务器 Task、Run 或 Job，也不会触发 provider、审批或发布。
          </p>
        </div>
        <span>非权威 · 本机</span>
      </div>

      {requestedDraftId && !initialDraft && (
        <div className="state-card" role="status">
          没有找到可安全读取的本地草稿。你可以从空白 brief 继续。
        </div>
      )}

      <form
        className="new-task-layout"
        onChange={() => {
          setError(null);
          setInvalidField(null);
        }}
        onSubmit={submit}
      >
        <div className="new-task-form">
          <fieldset>
            <legend>这次复刻为了什么？</legend>
            <p>目标轨道影响证据要求，但不会新增第七种主机制。</p>
            <div className="new-task-options">
              <label>
                <input
                  checked={goalTrack === "product_replication"}
                  name="goal_track"
                  onChange={() => selectGoal("product_replication")}
                  type="radio"
                />
                <span><strong>产品复刻</strong>需要 Product Snapshot、Facts 与 Claim Gate。</span>
              </label>
              <label>
                <input
                  checked={goalTrack === "brand_voice_social_resonance"}
                  name="goal_track"
                  onChange={() => selectGoal("brand_voice_social_resonance")}
                  type="radio"
                />
                <span><strong>品牌声量 / Social Resonance</strong>研究亲子共鸣、注意力和分享机制。</span>
              </label>
            </div>
          </fieldset>

          <div className="new-task-fields">
            <label htmlFor="task-subject">主题</label>
            <input {...invalidFieldProps("task-subject")} id="task-subject" maxLength={300} required value={subject} onChange={(event) => setSubject(event.target.value)} />
            <label htmlFor="task-question">决策问题</label>
            <textarea {...invalidFieldProps("task-question")} id="task-question" maxLength={1000} required rows={3} value={decisionQuestion} onChange={(event) => setDecisionQuestion(event.target.value)} />
            <label htmlFor="task-reference">公开参考链接</label>
            <input {...invalidFieldProps("task-reference")} id="task-reference" maxLength={2048} required type="url" value={referenceUrl} onChange={(event) => setReferenceUrl(event.target.value)} />
            <small>只记录公开 HTTP/HTTPS 链接；保存草稿不会访问、抓取或下载内容。</small>
          </div>

          <fieldset>
            <legend>产品声明范围</legend>
            <div className="new-task-options compact-options">
              <label>
                <input checked={claimScope === "no_product_claims"} disabled={goalTrack === "product_replication"} name="claim_scope" onChange={() => selectClaimScope("no_product_claims")} type="radio" />
                <span>不包含产品声明</span>
              </label>
              <label>
                <input checked={claimScope === "product_claims"} name="claim_scope" onChange={() => selectClaimScope("product_claims")} type="radio" />
                <span>包含产品声明</span>
              </label>
            </div>
            {claimScope === "product_claims" ? (
              <div className="new-task-fields inline-field">
                <label htmlFor="product-snapshot-id">Product Snapshot ID</label>
                <input {...invalidFieldProps("product-snapshot-id")} id="product-snapshot-id" maxLength={128} required value={productSnapshotId} onChange={(event) => setProductSnapshotId(event.target.value)} />
                <small>这里只记录候选引用；未来提交时仍须从 PostgreSQL 重新验证。</small>
              </div>
            ) : (
              <p>当前不引入产品声明，因此 Brand Voice 草稿不要求 Product Snapshot。</p>
            )}
          </fieldset>

          <fieldset>
            <legend>投放语境与观察窗口</legend>
            <div className="new-task-grid">
              <label htmlFor="task-platform">平台</label>
              <select id="task-platform" value={platform} onChange={(event) => setPlatform(event.target.value as DraftPlatform)}>
                <option value="tiktok">TikTok</option><option value="instagram">Instagram</option><option value="youtube">YouTube</option><option value="other">其他</option>
              </select>
              <label htmlFor="task-market">市场代码</label>
              <input {...invalidFieldProps("task-market")} id="task-market" maxLength={2} pattern="[A-Za-z]{2}" required value={market} onChange={(event) => setMarket(event.target.value)} />
              <label htmlFor="task-language">语言</label>
              <input {...invalidFieldProps("task-language")} id="task-language" maxLength={64} required value={language} onChange={(event) => setLanguage(event.target.value)} />
              <label htmlFor="window-start">观察开始日期</label>
              <input {...invalidFieldProps("window-start")} id="window-start" required type="date" value={windowStart} onChange={(event) => setWindowStart(event.target.value)} />
              <label htmlFor="window-end">观察结束日期</label>
              <input {...invalidFieldProps("window-end")} id="window-end" min={windowStart || undefined} required type="date" value={windowEnd} onChange={(event) => setWindowEnd(event.target.value)} />
              <label htmlFor="task-timezone">时区</label>
              <input {...invalidFieldProps("task-timezone")} id="task-timezone" maxLength={64} required value={timezone} onChange={(event) => setTimezone(event.target.value)} />
            </div>
          </fieldset>

          <fieldset>
            <legend>停止条件与人工边界</legend>
            <div className="new-task-fields">
              <label htmlFor="task-stop-condition">停止条件</label>
              <textarea {...invalidFieldProps("task-stop-condition")} id="task-stop-condition" maxLength={1000} required rows={2} value={stopCondition} onChange={(event) => setStopCondition(event.target.value)} />
              <label htmlFor="rights-state">权利初始状态</label>
              <select id="rights-state" value={rightsState} onChange={(event) => setRightsState(event.target.value as DraftRightsState)}>
                <option value="unknown">未知</option><option value="confirmed_for_analysis">仅确认可分析</option><option value="analysis_only">仅限分析</option><option value="restricted">受限</option><option value="blocked">阻断</option>
              </select>
              <label htmlFor="child-safety-state">儿童安全初始状态</label>
              <select id="child-safety-state" value={childSafetyState} onChange={(event) => setChildSafetyState(event.target.value as DraftChildSafetyState)}>
                <option value="review_required">需要人工审查</option><option value="unknown">未知</option><option value="not_applicable_user_asserted">用户声明不适用</option><option value="restricted">受限</option><option value="blocked">阻断</option>
              </select>
            </div>
            <div className="new-task-boundary">
              <strong>本草稿不会批准任何事项</strong>
              <p>儿童媒体使用权、商业授权和平台发布资格必须分别由人确认。</p>
              <label><input required type="checkbox" checked={rightsAcknowledged} onChange={(event) => setRightsAcknowledged(event.target.checked)} />权利仍需单独人工确认</label>
              <label><input required type="checkbox" checked={childSafetyAcknowledged} onChange={(event) => setChildSafetyAcknowledged(event.target.checked)} />儿童安全仍需单独人工确认</label>
            </div>
          </fieldset>

          {error && <div className="inline-error" id="new-task-error" role="alert">{error}</div>}
          <button className="button button-primary" type="submit">保存到本浏览器</button>
        </div>

        <aside className="new-task-preview" aria-label="草稿处理范围">
          <p className="eyebrow">LIVE PLAN PREVIEW</p>
          <h2>SV-Agent 将如何处理</h2>
          <p>当前只记录 brief，后续才能接入参考、拆解机制并请求人工决定。</p>
          <ol><li>记录参考来源与使用边界</li><li>检查 Task brief 是否完整</li><li>等待未来服务器写入门</li></ol>
          <div className="new-task-no-effects"><strong>本次不会执行</strong><span>PostgreSQL 写入</span><span>Run / Job / provider</span><span>Approval / Render / Publish</span></div>
        </aside>
      </form>
    </section>
  );
}
