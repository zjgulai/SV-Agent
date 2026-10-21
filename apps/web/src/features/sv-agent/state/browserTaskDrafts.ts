export const TASK_DRAFT_STORAGE_KEY = "sv-agent-task-drafts/v1";

export interface BrowserTaskDraft {
  draft_id: string;
  subject: string;
  decision_question: string;
  updated_at: string;
}

export interface BrowserTaskDraftRead {
  drafts: BrowserTaskDraft[];
  invalidDraftIgnored: boolean;
}

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

function parseDraft(value: unknown): BrowserTaskDraft | null {
  if (!isRecord(value)) return null;
  if (
    !boundedString(value.draft_id, 100) ||
    !boundedString(value.subject, 300) ||
    !boundedString(value.decision_question, 1000) ||
    !boundedString(value.updated_at, 64) ||
    Number.isNaN(Date.parse(value.updated_at))
  ) {
    return null;
  }
  return {
    draft_id: value.draft_id,
    subject: value.subject,
    decision_question: value.decision_question,
    updated_at: value.updated_at,
  };
}

export function readBrowserTaskDrafts(storage: Storage | null): BrowserTaskDraftRead {
  if (!storage) return { drafts: [], invalidDraftIgnored: false };

  try {
    const serialized = storage.getItem(TASK_DRAFT_STORAGE_KEY);
    if (!serialized) return { drafts: [], invalidDraftIgnored: false };
    const value: unknown = JSON.parse(serialized);
    if (
      !isRecord(value) ||
      value.schema_version !== "sv-task-drafts/v1" ||
      !Array.isArray(value.drafts)
    ) {
      return { drafts: [], invalidDraftIgnored: true };
    }
    const drafts = value.drafts.slice(0, 20).map(parseDraft);
    return {
      drafts: drafts.filter((draft): draft is BrowserTaskDraft => draft !== null),
      invalidDraftIgnored:
        value.drafts.length > 20 || drafts.some((draft) => draft === null),
    };
  } catch {
    return { drafts: [], invalidDraftIgnored: true };
  }
}

export function readBrowserTaskDraftsFrom(
  getStorage: () => Storage | null,
): BrowserTaskDraftRead {
  try {
    return readBrowserTaskDrafts(getStorage());
  } catch {
    return { drafts: [], invalidDraftIgnored: true };
  }
}

