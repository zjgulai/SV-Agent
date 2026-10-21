export const NEW_TASK_DRAFT_STORAGE_KEY = "sv-agent-new-task-drafts/v2";

const MAX_DRAFTS = 20;
const MAX_ENVELOPE_BYTES = 256 * 1024;

export type DraftGoalTrack =
  | "product_replication"
  | "brand_voice_social_resonance";
export type DraftPlatform = "tiktok" | "instagram" | "youtube" | "other";
export type DraftClaimScope = "product_claims" | "no_product_claims";
export type DraftRightsState =
  | "confirmed_for_analysis"
  | "analysis_only"
  | "unknown"
  | "restricted"
  | "blocked";
export type DraftChildSafetyState =
  | "unknown"
  | "review_required"
  | "not_applicable_user_asserted"
  | "restricted"
  | "blocked";

export interface BrowserNewTaskDraft {
  draft_id: string;
  created_at: string;
  updated_at: string;
  goal_track: DraftGoalTrack;
  decision_question: string;
  reference_url: string;
  subject: string;
  platform: DraftPlatform;
  market: string;
  language: string;
  performance_window: {
    start: string;
    end: string;
    timezone: string;
  };
  stop_condition: string;
  claim_scope: DraftClaimScope;
  product_snapshot_id: string | null;
  initial_rights_state: DraftRightsState;
  initial_child_safety_state: DraftChildSafetyState;
  boundary_acknowledgements: {
    rights_requires_separate_human_gate: boolean;
    child_safety_requires_separate_human_gate: boolean;
  };
}

export interface BrowserNewTaskDraftRead {
  drafts: BrowserNewTaskDraft[];
  invalidDraftIgnored: boolean;
}

export type BrowserNewTaskDraftWrite =
  | { ok: true }
  | { ok: false; reason: "invalid_draft" | "storage_unavailable" | "storage_limit" };

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function boundedString(value: unknown, maxLength: number): value is string {
  return (
    typeof value === "string" &&
    value.length > 0 &&
    value.length <= maxLength &&
    value === value.trim()
  );
}

function isTimestamp(value: unknown): value is string {
  return boundedString(value, 64) && !Number.isNaN(Date.parse(value));
}

function isCalendarDate(value: unknown): value is string {
  if (typeof value !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
  const parsed = new Date(`${value}T00:00:00Z`);
  return !Number.isNaN(parsed.valueOf()) && parsed.toISOString().slice(0, 10) === value;
}

function isPublicReference(value: unknown): value is string {
  if (!boundedString(value, 2048)) return false;
  try {
    const parsed = new URL(value);
    return (
      (parsed.protocol === "https:" || parsed.protocol === "http:") &&
      !parsed.username &&
      !parsed.password
    );
  } catch {
    return false;
  }
}

function isOneOf<T extends string>(value: unknown, allowed: readonly T[]): value is T {
  return typeof value === "string" && allowed.includes(value as T);
}

function parseDraft(value: unknown): BrowserNewTaskDraft | null {
  if (!isRecord(value) || !isRecord(value.performance_window)) return null;
  if (!isRecord(value.boundary_acknowledgements)) return null;
  if (
    !boundedString(value.draft_id, 100) ||
    !isTimestamp(value.created_at) ||
    !isTimestamp(value.updated_at) ||
    Date.parse(value.updated_at) < Date.parse(value.created_at) ||
    !isOneOf(value.goal_track, ["product_replication", "brand_voice_social_resonance"] as const) ||
    !boundedString(value.decision_question, 1000) ||
    !isPublicReference(value.reference_url) ||
    !boundedString(value.subject, 300) ||
    !isOneOf(value.platform, ["tiktok", "instagram", "youtube", "other"] as const) ||
    typeof value.market !== "string" ||
    !/^[A-Z]{2}$/.test(value.market) ||
    !boundedString(value.language, 64) ||
    !isCalendarDate(value.performance_window.start) ||
    !isCalendarDate(value.performance_window.end) ||
    value.performance_window.end < value.performance_window.start ||
    !boundedString(value.performance_window.timezone, 64) ||
    !boundedString(value.stop_condition, 1000) ||
    !isOneOf(value.claim_scope, ["product_claims", "no_product_claims"] as const) ||
    !isOneOf(value.initial_rights_state, [
      "confirmed_for_analysis",
      "analysis_only",
      "unknown",
      "restricted",
      "blocked",
    ] as const) ||
    !isOneOf(value.initial_child_safety_state, [
      "unknown",
      "review_required",
      "not_applicable_user_asserted",
      "restricted",
      "blocked",
    ] as const) ||
    value.boundary_acknowledgements.rights_requires_separate_human_gate !== true ||
    value.boundary_acknowledgements.child_safety_requires_separate_human_gate !== true
  ) {
    return null;
  }

  const productSnapshotId = value.product_snapshot_id;
  if (productSnapshotId !== null && !boundedString(productSnapshotId, 128)) return null;
  if (value.claim_scope === "product_claims" && productSnapshotId === null) return null;
  if (value.claim_scope === "no_product_claims" && productSnapshotId !== null) return null;
  if (value.goal_track === "product_replication" && value.claim_scope !== "product_claims") {
    return null;
  }

  return {
    draft_id: value.draft_id,
    created_at: value.created_at,
    updated_at: value.updated_at,
    goal_track: value.goal_track,
    decision_question: value.decision_question,
    reference_url: value.reference_url,
    subject: value.subject,
    platform: value.platform,
    market: value.market,
    language: value.language,
    performance_window: {
      start: value.performance_window.start,
      end: value.performance_window.end,
      timezone: value.performance_window.timezone,
    },
    stop_condition: value.stop_condition,
    claim_scope: value.claim_scope,
    product_snapshot_id: productSnapshotId,
    initial_rights_state: value.initial_rights_state,
    initial_child_safety_state: value.initial_child_safety_state,
    boundary_acknowledgements: {
      rights_requires_separate_human_gate: true,
      child_safety_requires_separate_human_gate: true,
    },
  };
}

export function readBrowserNewTaskDrafts(
  storage: Storage | null,
): BrowserNewTaskDraftRead {
  if (!storage) return { drafts: [], invalidDraftIgnored: false };
  try {
    const serialized = storage.getItem(NEW_TASK_DRAFT_STORAGE_KEY);
    if (!serialized) return { drafts: [], invalidDraftIgnored: false };
    if (new TextEncoder().encode(serialized).byteLength > MAX_ENVELOPE_BYTES) {
      return { drafts: [], invalidDraftIgnored: true };
    }
    const value: unknown = JSON.parse(serialized);
    if (
      !isRecord(value) ||
      value.schema_version !== "sv-new-task-drafts/v2" ||
      !Array.isArray(value.drafts)
    ) {
      return { drafts: [], invalidDraftIgnored: true };
    }
    const parsed = value.drafts.slice(0, MAX_DRAFTS).map(parseDraft);
    return {
      drafts: parsed.filter((draft): draft is BrowserNewTaskDraft => draft !== null),
      invalidDraftIgnored:
        value.drafts.length > MAX_DRAFTS || parsed.some((draft) => draft === null),
    };
  } catch {
    return { drafts: [], invalidDraftIgnored: true };
  }
}

export function readBrowserNewTaskDraftsFrom(
  getStorage: () => Storage | null,
): BrowserNewTaskDraftRead {
  try {
    return readBrowserNewTaskDrafts(getStorage());
  } catch {
    return { drafts: [], invalidDraftIgnored: true };
  }
}

export function saveBrowserNewTaskDraft(
  storage: Storage | null,
  draft: BrowserNewTaskDraft,
): BrowserNewTaskDraftWrite {
  if (!storage) return { ok: false, reason: "storage_unavailable" };
  if (parseDraft(draft) === null) return { ok: false, reason: "invalid_draft" };
  try {
    const current = readBrowserNewTaskDrafts(storage).drafts;
    const envelope = {
      schema_version: "sv-new-task-drafts/v2",
      drafts: [draft, ...current.filter((item) => item.draft_id !== draft.draft_id)].slice(
        0,
        MAX_DRAFTS,
      ),
    };
    const serialized = JSON.stringify(envelope);
    if (new TextEncoder().encode(serialized).byteLength > MAX_ENVELOPE_BYTES) {
      return { ok: false, reason: "storage_limit" };
    }
    storage.setItem(NEW_TASK_DRAFT_STORAGE_KEY, serialized);
    return { ok: true };
  } catch {
    return { ok: false, reason: "storage_unavailable" };
  }
}
