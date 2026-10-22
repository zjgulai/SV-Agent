export type FactStatus = "proposed" | "confirmed" | "rejected" | "locked";

export interface ProductFact {
  id: string;
  snapshot_id: string;
  claim_type: string;
  claim: string;
  value: Record<string, unknown>;
  evidence_kind: string;
  evidence_locator: string;
  evidence_excerpt: string;
  confidence: string;
  status: FactStatus;
  updated_at: string;
}

export interface ProductSnapshot {
  id: string;
  source_id: string;
  title: string;
  description: string | null;
  category_path: string[];
  images: string[];
  price_amount: string | null;
  price_currency: string | null;
  canonical_digest: string;
  created_at: string;
}

export interface Product {
  product_id: string;
  snapshot: ProductSnapshot;
  facts: ProductFact[];
}

export interface ProblemDetails {
  type: string;
  title: string;
  status: number;
  detail: string;
  code: string;
  request_id: string;
}

export type TaskInboxLane =
  | "needs_decision"
  | "needs_input"
  | "blocked"
  | "technical_attention"
  | "agent_running"
  | "completed_with_limits"
  | "stopped"
  | "not_started";

export type TaskInboxOrderingReason =
  | "human_decision_required"
  | "user_input_required"
  | "business_blocker_present"
  | "runtime_integrity_attention"
  | "technical_failure_requires_review"
  | "agent_work_in_progress"
  | "completed_with_declared_limits"
  | "stopped_by_decision"
  | "run_not_started";

export interface TaskInboxItem {
  task_id: string;
  task_revision: number;
  goal_track: "product_replication" | "brand_voice_social_resonance";
  subject: string;
  decision_question: string;
  active_run_id: string | null;
  active_run_revision: number | null;
  run_state:
    | "draft"
    | "planning"
    | "awaiting_input"
    | "runnable"
    | "running"
    | "awaiting_approval"
    | "blocked"
    | "completed_with_limits"
    | "failed"
    | "stopped"
    | null;
  pending_decision_count: number;
  pending_gate_kinds: string[];
  lane: TaskInboxLane;
  ordering_reason: TaskInboxOrderingReason;
  priority_at: string;
}

export interface TaskInboxProjection {
  schema_version: "sv-task-inbox/v1";
  authority: "postgresql";
  ordering_policy_version: "sv-task-inbox-order/v1";
  items: TaskInboxItem[];
  truncated: boolean;
}

export type MissionControlRunState = Exclude<TaskInboxItem["run_state"], null>;
export type MissionControlStageStatus =
  | "completed"
  | "active"
  | "waiting"
  | "blocked"
  | "unknown";
export type MissionControlStageKey =
  | "reference_admission"
  | "content_decomposition"
  | "mechanism_selection"
  | "fact_and_contract"
  | "adaptation"
  | "script_and_storyboard"
  | "media_integrity_and_finding";
export type AgentCommandIntent =
  | "provide_input"
  | "request_plan"
  | "request_evidence"
  | "revise_plan"
  | "advance"
  | "resume_recovery"
  | "stop";

export interface MissionControlProjection {
  schema_version: "sv-mission-control/v1";
  authority: "postgresql";
  task: {
    task_id: string;
    task_revision: number;
    goal_track: TaskInboxItem["goal_track"];
    decision_question: string;
    subject: string;
    platform: "tiktok" | "instagram" | "youtube" | "other";
    market: string;
    language: string;
    performance_window: { start: string; end: string; timezone: string };
    stop_condition: string;
    initial_rights_state:
      | "confirmed_for_analysis"
      | "analysis_only"
      | "unknown"
      | "restricted"
      | "blocked";
  };
  run: {
    run_id: string;
    task_revision: number;
    run_revision: number;
    state: MissionControlRunState;
    primary_mechanism: string | null;
    creative_dimension: string | null;
    updated_at: string;
  } | null;
  stages: Array<{
    key: MissionControlStageKey;
    label: string;
    status: MissionControlStageStatus;
  }>;
  current_stage: MissionControlStageKey;
  plan: {
    ref: string;
    version: number;
    workflow_name: string;
    workflow_version: string;
    capability_catalog_version: string;
    run_revision: number;
    steps: Array<{
      step_id: string;
      order: number;
      capability_name: string;
      capability_version: string;
      execution_mode: string;
    }>;
    limitations: string[];
    created_at: string;
  } | null;
  blockers: Array<{ code: string; message: string; source_ref: string }>;
  next_safe_action: {
    kind: string;
    label: string;
    reason: string;
    reason_code: string;
    interaction_intent: AgentCommandIntent | null;
    basis_refs: string[];
    explicit_non_effects: string[];
    execution_available: false;
  };
  tool_runs: Array<{
    ref: string;
    tool_name: string;
    tool_version: string;
    intent_summary: string;
    effect_class: "read" | "write";
    status: "pending" | "running" | "completed" | "failed" | "unavailable" | "unknown";
    stable_error_code: string | null;
    recovery_action: string | null;
    started_at: string | null;
    finished_at: string | null;
    updated_at: string;
  }>;
  tool_runs_truncated: boolean;
  current_artifact: {
    ref: string;
    artifact_type:
      | "reference_bundle"
      | "decomposition_map"
      | "pattern_hypothesis"
      | "replication_plan"
      | "fact_map"
      | "replication_contract"
      | "adaptation_package"
      | "media_integrity_record"
      | "replication_finding";
    version: number;
    status:
      | "draft"
      | "validated"
      | "awaiting_approval"
      | "blocked"
      | "approved"
      | "stale"
      | "superseded"
      | "final_with_limits";
    evidence_level: "fact" | "inference" | "unknown";
    proof_level: "local" | "ci" | "private" | "deployment" | "live" | "production";
    created_at: string;
  } | null;
  explanation: {
    summary: string;
    citations: Array<{ kind: string; ref: string }>;
  };
}

export type EvidenceArtifactType = NonNullable<
  MissionControlProjection["current_artifact"]
>["artifact_type"];
export type EvidenceArtifactStatus = NonNullable<
  MissionControlProjection["current_artifact"]
>["status"];
export type EvidenceLevel = NonNullable<
  MissionControlProjection["current_artifact"]
>["evidence_level"];
export type ProofLevel = NonNullable<
  MissionControlProjection["current_artifact"]
>["proof_level"];
export type EvidencePlaneKind =
  | "product_truth"
  | "performance"
  | "experiment"
  | "asset";
export type EvidenceAvailabilityState =
  | "available"
  | "unavailable"
  | "out_of_scope"
  | "quarantined";

export interface EvidenceSubjectSummary {
  state:
    | "exact_snapshot"
    | "reviewed_snapshot_selection"
    | "reviewed_family_context"
    | "unresolved"
    | "conflict"
    | "not_applicable";
  market: string | null;
  locale: string | null;
  limitations: string[];
}

export interface EvidenceWindowSummary {
  start: string;
  end: string;
  timezone: string;
  basis: "artifact_observation" | "task_scope";
}

export interface EvidenceArtifactsProjection {
  schema_version: "sv-evidence-artifacts/v1";
  authority: "postgresql";
  task: {
    task_id: string;
    task_revision: number;
    subject: string;
    performance_window: { start: string; end: string; timezone: string };
  };
  run: {
    run_id: string;
    run_revision: number;
    state: MissionControlRunState;
  } | null;
  graph: {
    state: "available" | "unavailable";
    public_code: string;
    nodes: Array<{
      ref: string;
      artifact_type: EvidenceArtifactType;
      version: number;
      status: EvidenceArtifactStatus;
      evidence_level: EvidenceLevel;
      proof_level: ProofLevel;
      created_at: string;
      is_conclusion: boolean;
      sources: Array<{ kind: string }>;
      subject: EvidenceSubjectSummary;
      window: EvidenceWindowSummary | null;
      limitations: string[];
    }>;
    edges: Array<{
      source_ref: string;
      target_ref: string;
      kind: "declared_input" | "runtime_verified";
      verification_state: "declared_only" | "verified";
    }>;
    limitations: string[];
  };
  evidence_planes: Array<{
    kind: EvidencePlaneKind;
    state: EvidenceAvailabilityState;
    public_code: string;
    source: string;
    subject: EvidenceSubjectSummary | null;
    window: EvidenceWindowSummary | null;
    proof_level: ProofLevel | null;
    limitations: string[];
  }>;
  comparison:
    | {
        state: "available";
        public_code: string;
        script_ref: string;
        control_version_ref: string;
        variant_version_ref: string;
        limitations: string[];
      }
    | {
        state: "unavailable";
        public_code: "COMPARISON_VERSION_REFS_UNAVAILABLE";
        script_ref: null;
        control_version_ref: null;
        variant_version_ref: null;
        limitations: string[];
      };
  explicit_non_effects: string[];
}

export type ApprovalDecision =
  | "approve"
  | "reject"
  | "request_evidence"
  | "stop";
export type ApprovalDecisionState = "pending" | "decided";
export type ApprovalScopeState = "current" | "stale";
export type ApprovalGateKind =
  | "fact"
  | "replication_contract"
  | "storyboard"
  | "reference_rights"
  | "child_safety"
  | "media_integrity"
  | "source_use"
  | "originality"
  | "legal"
  | "commercial"
  | "platform"
  | "deployment"
  | "production";
export type ReplayTimelineKind =
  | "task_event"
  | "plan_revision"
  | "artifact_revision"
  | "approval_request"
  | "tool_run"
  | "decision";

export interface ApprovalReplayProjection {
  schema_version: "sv-approval-replay/v1";
  authority: "postgresql";
  task: {
    task_id: string;
    task_revision: number;
    subject: string;
  };
  run: {
    run_id: string;
    run_revision: number;
    state: MissionControlRunState;
  } | null;
  summary: {
    pending: number;
    decided: number;
    stale: number;
  };
  decision_vocabulary: ApprovalDecision[];
  decision_available: false;
  approvals: Array<{
    request_version: number;
    gate_kind: ApprovalGateKind;
    target_artifact_type: EvidenceArtifactType;
    target_version: number;
    decision_state: ApprovalDecisionState;
    scope_state: ApprovalScopeState;
    predicted_effects: string[];
    explicit_non_effects: string[];
    evidence: string[];
    limitations: string[];
    stale_conditions: string[];
    decision: ApprovalDecision | null;
    decided_at: string | null;
    audit: {
      task_revision: number;
      run_revision: number;
    };
  }>;
  approvals_truncated: boolean;
  timeline: {
    snapshot_through_sequence: number;
    next_after_sequence: number | null;
    truncated: boolean;
    entries: Array<{
      event_sequence: number;
      kind: ReplayTimelineKind;
      event_type: string;
      summary: string;
      task_revision: number;
      run_revision: number | null;
    }>;
  };
  explicit_non_effects: string[];
}

export class ApiProblem extends Error {
  constructor(public readonly problem: ProblemDetails) {
    super(problem.detail);
  }
}

export class ApiTransportError extends Error {
  constructor() {
    super("请求状态未知，请恢复原请求。");
  }
}

export class ApiResponseParseError extends Error {
  constructor(public readonly jobPath: string | null) {
    super(jobPath ? "任务已受理，正在恢复任务。" : "请求状态未知，请恢复原请求。");
  }
}

export interface Job {
  id: string;
  job_type: "product_import" | "script_generation";
  state:
    | "queued"
    | "fetching"
    | "parsing"
    | "generating"
    | "validating"
    | "succeeded"
    | "failed"
    | "validation_failed";
  attempt_count: number;
  error_code: string | null;
  error_detail: string | null;
  result_id: string | null;
}

export interface JobEvent {
  id: string;
  event_type: string;
  from_state: Job["state"] | null;
  to_state: Job["state"];
  attempt_count: number;
  error_code: string | null;
  error_detail: string | null;
  event_sequence: number;
  created_at: string;
}

export interface CreativePattern {
  key: string;
  version: string;
  name: string;
  supported_durations: number[];
  supported_languages: string[];
  contracts: PatternDefinition[];
}

export interface PatternDefinition {
  contract_version: "p1.3a" | "p1.3b" | "p1.3c";
  key: string;
  version: string;
  name: string;
  hook_type: string;
  duration_seconds: number;
  language: "en" | "zh-CN";
  phases: Array<{
    key: string;
    purpose: string;
    shot_role: string;
    fact_role: "required_selected";
  }>;
  shots: Array<{
    phase_key: string;
    role: string;
    fact_role: "required_selected";
    budget_weight: number;
  }>;
  speaking_rate: {
    unit: "words_per_second" | "han_characters_per_second";
    max: number;
  };
  field_policy: {
    fact_bound: string[];
    server_owned: string[];
  };
  cta_policy: { mode: "server_generic_no_offer" | "server_promotion_final_cta" };
  audience_policy: {
    mode: "record_only" | "server_owned_profile";
    allowed_slots: string[];
    profile_key?: "general" | "study_routine" | "work_routine" | "home_routine" | "on_the_go";
  };
  acceptance_checks: string[];
}

export interface ScriptPhase {
  key: string;
  purpose: string;
  start_seconds: number;
  end_seconds: number;
}

export interface ScriptShot {
  start_seconds: number;
  end_seconds: number;
  phase_key: string;
  role: string | null;
  voiceover: string;
  visual: string;
  action: string;
  caption: string;
  acceptance_shot: string;
  supported_fact_ids: string[];
  product_claims: string[];
  promotion?: { fact_id: string; text: string } | null;
}

export interface ValidationFinding {
  rule_id: string;
  path: string;
  message: string;
  severity: "blocking" | "warning";
  evidence: string | null;
}

export interface ScriptVersion {
  id: string;
  generation_id: string;
  parent_version_id: string | null;
  revision_kind: "fact_rebind" | null;
  actor_kind: "local_operator" | null;
  reason_code: "fact_rebind" | null;
  operation_input_digest: string | null;
  created_at: string;
  draft: {
    target_duration_seconds: number;
    language: string;
    audience: string;
    snapshot_id: string;
    phases: ScriptPhase[];
    shots: ScriptShot[];
    titles: string[];
    tags: string[];
    shooting_list: string[];
  };
  validation_report: {
    acceptable: boolean;
    findings: ValidationFinding[];
    blocking: ValidationFinding[];
  };
}

export interface ScriptResource {
  generation: {
    id: string;
    snapshot_id: string;
    selected_fact_ids: string[];
    excluded_fact_ids: string[];
    configuration: Record<string, unknown>;
    pattern_key: string;
    pattern_version: string;
    provider: string;
    model: string;
    prompt_contract_version: string;
    input_digest: string;
    created_at: string;
  };
  versions: ScriptVersion[];
  fact_contract: {
    selected: Array<{
      id: string;
      claim: string;
      status: FactStatus;
      snapshot_id: string;
    }>;
    excluded: Array<{
      id: string;
      claim: string;
      status: FactStatus;
      snapshot_id: string;
    }>;
  };
}

export interface StoryboardFact {
  id: string;
  claim_type: string;
  claim: string;
  evidence_kind: string;
  evidence_excerpt: string;
  status: FactStatus;
}

export interface StoryboardPreflight {
  status: "ready" | "blocked";
  script_id: string;
  version_id: string;
  snapshot_id: string;
  pattern_key: string;
  input_digest: string;
  selected_facts: StoryboardFact[];
  excluded_facts: StoryboardFact[];
  phases: ScriptPhase[];
  shots: ScriptShot[];
  validation_report: ScriptVersion["validation_report"];
}

export interface StoryboardVersion {
  id: string;
  script_version_id: string;
  snapshot_id: string;
  selected_fact_ids: string[];
  excluded_fact_ids: string[];
  pattern_key: string;
  pattern_version: string;
  phase_sequence: string[];
  draft: ScriptVersion["draft"];
  validation_report: ScriptVersion["validation_report"];
  preflight_digest: string;
  storyboard_digest: string;
  preview_contract_version: string;
  created_at: string;
}

export interface StoryboardPreview {
  storyboard_id: string;
  storyboard_digest: string;
  preview_digest: string;
  preview_contract_version: string;
  image_indexes: number[];
  shots: Array<ScriptShot & { index: number }>;
}

export interface StoryboardApprovalEvent {
  id: string;
  storyboard_id: string;
  decision: "approved" | "rejected";
  reason: string | null;
  storyboard_digest: string;
  preflight_digest: string;
  approval_digest: string;
  validation_report: ScriptVersion["validation_report"];
  event_sequence: number;
  created_at: string;
}

export interface StoryboardApproval {
  status: "unreviewed" | "approved" | "rejected" | "stale";
  latest_event: StoryboardApprovalEvent | null;
}

export interface VersionDiff {
  added: Array<{ path: string; value: unknown }>;
  removed: Array<{ path: string; value: unknown }>;
  changed: Array<{ path: string; left: unknown; right: unknown }>;
}

export interface ComparisonFinding {
  code: string;
  context: "identity" | "comparability" | "product_truth" | "script_validation" | "storyboard" | "performance" | "experiment" | "asset";
  path: string | null;
  message: string;
}

export interface ComparisonCandidate {
  version_id: string;
  parent_version_id: string | null;
  created_at: string;
  draft: ScriptVersion["draft"];
  stored_validation_report: ScriptVersion["validation_report"];
  live_validation_report: ScriptVersion["validation_report"];
  storyboard_readiness: "ready" | "blocked";
}

export interface SemanticDifference {
  section: "script" | "storyboard" | "asset";
  path: string;
  change: "added" | "removed" | "changed";
  kind: "declared_dimension" | "unexpected_change" | "fact_binding_change" | "unverified";
  control_present: boolean;
  variant_present: boolean;
  control: unknown | null;
  variant: unknown | null;
}

export interface ComparisonFact {
  id: string;
  availability: "present" | "missing";
  claim: string | null;
  status: FactStatus | null;
}

export interface ComparisonEvidence {
  availability: "available" | "unavailable" | "quarantined";
  source_reference: string;
  limitation: string;
}

export interface CreativeComparisonProjection {
  schema_version: "creative-comparison-view-v1";
  script_id: string;
  observed_at: string;
  readiness: {
    state: "blocked" | "needs_evidence" | "reviewable";
    disposition: "revise" | "collect_evidence" | "stop";
    single_variable_status: "unverified";
    blockers: ComparisonFinding[];
    evidence_needs: ComparisonFinding[];
  };
  control: ComparisonCandidate;
  variant: ComparisonCandidate;
  differences: SemanticDifference[];
  product_truth_gate: {
    status: "pass" | "blocked";
    snapshot_id: string;
    pattern_key: string;
    pattern_version: string;
    selected_facts: ComparisonFact[];
    excluded_facts: ComparisonFact[];
  };
  performance_evidence: ComparisonEvidence;
  experiment_evidence: ComparisonEvidence;
  asset_evidence: ComparisonEvidence;
  limitations: ComparisonFinding[];
  projection_digest: string;
}

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "";

export function safeJobPathFromLocation(location: string | null): string | null {
  if (!location) return null;
  try {
    const resolved = new URL(location, globalThis.location?.origin ?? "http://localhost");
    if (resolved.origin !== (globalThis.location?.origin ?? resolved.origin) || resolved.search || resolved.hash) return null;
    const match = resolved.pathname.match(/^\/api\/v1\/jobs\/([A-Za-z0-9-]+)$/);
    return match ? `/jobs/${match[1]}` : null;
  } catch {
    return null;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", ...init?.headers },
    });
  } catch {
    throw new ApiTransportError();
  }
  if (!response.ok) {
    const fallback: ProblemDetails = {
      type: "about:blank",
      title: "请求失败",
      status: response.status,
      detail: `请求失败（${response.status}）`,
      code: "HTTP_ERROR",
      request_id: "unknown",
    };
    let problem = fallback;
    try {
      problem = { ...fallback, ...(await response.json()) } as ProblemDetails;
    } catch {
      // Keep a stable fallback when a proxy returns non-JSON.
    }
    throw new ApiProblem(problem);
  }
  try {
    return (await response.json()) as T;
  } catch {
    throw new ApiResponseParseError(safeJobPathFromLocation(response.headers.get("Location")));
  }
}

export const api = {
  listSvAgentTasks: () => request<TaskInboxProjection>("/api/v1/sv-agent/tasks"),
  getSvAgentMissionControl: (taskId: string) =>
    request<MissionControlProjection>(
      `/api/v1/sv-agent/tasks/${encodeURIComponent(taskId)}`,
    ),
  getSvAgentEvidenceArtifacts: (taskId: string) =>
    request<EvidenceArtifactsProjection>(
      `/api/v1/sv-agent/tasks/${encodeURIComponent(taskId)}/artifacts`,
    ),
  getSvAgentApprovalReplay: (taskId: string) =>
    request<ApprovalReplayProjection>(
      `/api/v1/sv-agent/tasks/${encodeURIComponent(taskId)}/replay`,
    ),
  listProducts: () => request<Product[]>("/api/v1/products"),
  getProduct: (id: string) => request<Product>(`/api/v1/products/${id}`),
  createProduct: (input: {
    title: string;
    description: string;
    category_path: string[];
    images: string[];
    price?: { amount: string; currency: string };
    facts: Array<{
      claim_type: string;
      claim: string;
      value: Record<string, unknown>;
      evidence_excerpt: string;
    }>;
  }) => request<Product>("/api/v1/products", { method: "POST", body: JSON.stringify(input) }),
  transitionFact: (productId: string, factId: string, status: FactStatus) =>
    request<ProductFact>(`/api/v1/products/${productId}/facts/${factId}`, {
      method: "PATCH",
      body: JSON.stringify({ status }),
    }),
  createPromotionFact: (
    productId: string,
    input: { value: Record<string, unknown>; evidence_excerpt: string },
    idempotencyKey: string,
  ) =>
    request<ProductFact>(`/api/v1/products/${productId}/promotion-facts`, {
      method: "POST",
      headers: { "Idempotency-Key": idempotencyKey },
      body: JSON.stringify(input),
    }),
  importProduct: (url: string, idempotencyKey: string) =>
    request<{ id: string; state: string; source_id: string }>("/api/v1/product-imports", {
      method: "POST",
      headers: { "Idempotency-Key": idempotencyKey },
      body: JSON.stringify({ url }),
    }),
  createGeneration: (
    productId: string,
    input: {
      target_duration_seconds: number;
      language: string;
      audience: "general" | "study_routine" | "work_routine" | "home_routine" | "on_the_go";
      creative_pattern_key: string;
      selected_fact_ids: string[];
      excluded_fact_ids: string[];
      promotion_fact_id?: string | null;
    },
    idempotencyKey: string,
  ) =>
    request<Job>(`/api/v1/products/${productId}/script-generations`, {
      method: "POST",
      headers: { "Idempotency-Key": idempotencyKey },
      body: JSON.stringify(input),
    }),
  getJob: (id: string) => request<Job>(`/api/v1/jobs/${id}`),
  getJobEvents: (id: string) => request<JobEvent[]>(`/api/v1/jobs/${id}/events`),
  getPatterns: () => request<CreativePattern[]>("/api/v1/creative-patterns"),
  getStoryboardPreflight: (scriptId: string, versionId: string) =>
    request<StoryboardPreflight>(
      "/api/v1/scripts/" + scriptId + "/versions/" + versionId + "/storyboard-preflight",
    ),
  createStoryboard: (scriptId: string, versionId: string, idempotencyKey: string) =>
    request<StoryboardVersion>(
      `/api/v1/scripts/${scriptId}/versions/${versionId}/storyboards`,
      { method: "POST", headers: { "Idempotency-Key": idempotencyKey } },
    ),
  getStoryboard: (storyboardId: string) =>
    request<StoryboardVersion>(`/api/v1/storyboards/${storyboardId}`),
  getStoryboardPreview: (storyboardId: string) =>
    request<StoryboardPreview>(`/api/v1/storyboards/${storyboardId}/preview`),
  getStoryboardApproval: (storyboardId: string) =>
    request<StoryboardApproval>(`/api/v1/storyboards/${storyboardId}/approval`),
  createStoryboardApproval: (
    storyboardId: string,
    input: { decision: "approved" | "rejected"; reason?: string },
    idempotencyKey: string,
  ) =>
    request<StoryboardApprovalEvent>(
      `/api/v1/storyboards/${storyboardId}/approval-events`,
      {
        method: "POST",
        headers: { "Idempotency-Key": idempotencyKey },
        body: JSON.stringify(input),
      },
    ),
  getScript: (id: string) => request<ScriptResource>(`/api/v1/scripts/${id}`),
  deriveVersion: (
    scriptId: string,
    versionId: string,
    input: { fact_bindings: Array<{ shot_index: number; fact_id: string }> },
    idempotencyKey: string,
  ) =>
    request<ScriptVersion>(`/api/v1/scripts/${scriptId}/versions/${versionId}/derive`, {
      method: "POST",
      headers: { "Idempotency-Key": idempotencyKey },
      body: JSON.stringify(input),
    }),
  compareVersions: (id: string, left: string, right: string) =>
    request<VersionDiff>(`/api/v1/scripts/${id}/compare?left=${encodeURIComponent(left)}&right=${encodeURIComponent(right)}`),
  getCreativeComparison: (id: string, control: string, variant: string) =>
    request<CreativeComparisonProjection>(
      `/api/v1/scripts/${id}/creative-comparison?control=${encodeURIComponent(control)}&variant=${encodeURIComponent(variant)}`,
    ),
};
