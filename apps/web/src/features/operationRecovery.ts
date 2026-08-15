export type RecoverableOperationKind = "product_import" | "script_generation";

export type OperationState = "submitting" | "unknown" | "recovering" | "accepted";

export interface OperationRecord {
  schema_version: 1;
  idempotency_key: string;
  kind: RecoverableOperationKind;
  request: {
    route: string;
    body: unknown;
  };
  request_digest: string;
  job_path: string | null;
  state: OperationState;
  last_known_job_state: string | null;
  last_read_at: string | null;
  created_at: string;
  updated_at: string;
}

const STORAGE_KEY = "factframe.operation-recovery.v1";
const MAX_RECORDS = 20;

function stableJson(value: unknown): string {
  if (Array.isArray(value)) return `[${value.map(stableJson).join(",")}]`;
  if (value && typeof value === "object") {
    const record = value as Record<string, unknown>;
    return `{${Object.keys(record).sort().map((key) => `${JSON.stringify(key)}:${stableJson(record[key])}`).join(",")}}`;
  }
  return JSON.stringify(value);
}

function fingerprint(value: unknown): string {
  let hash = 0x811c9dc5;
  for (const char of stableJson(value)) {
    hash ^= char.charCodeAt(0);
    hash = Math.imul(hash, 0x01000193);
  }
  return (hash >>> 0).toString(16).padStart(8, "0");
}

function storage(): Storage | null {
  try {
    return globalThis.sessionStorage;
  } catch {
    return null;
  }
}

function readRecords(): OperationRecord[] {
  const value = storage()?.getItem(STORAGE_KEY);
  if (!value) return [];
  try {
    const records = JSON.parse(value) as unknown;
    if (!Array.isArray(records)) return [];
    return records.filter(isOperationRecord);
  } catch {
    return [];
  }
}

function isOperationRecord(value: unknown): value is OperationRecord {
  if (!value || typeof value !== "object") return false;
  const record = value as Partial<OperationRecord>;
  return record.schema_version === 1
    && typeof record.idempotency_key === "string"
    && (record.kind === "product_import" || record.kind === "script_generation")
    && typeof record.request?.route === "string"
    && typeof record.request_digest === "string"
    && (record.state === "submitting" || record.state === "unknown" || record.state === "recovering" || record.state === "accepted");
}

function writeRecords(records: OperationRecord[]) {
  storage()?.setItem(STORAGE_KEY, JSON.stringify(records.slice(-MAX_RECORDS)));
}

function newKey() {
  if (globalThis.crypto?.randomUUID) return globalThis.crypto.randomUUID();
  const bytes = new Uint8Array(16);
  for (let index = 0; index < bytes.length; index += 1) bytes[index] = Math.floor(Math.random() * 256);
  bytes[6] = (bytes[6] & 0x0f) | 0x40;
  bytes[8] = (bytes[8] & 0x3f) | 0x80;
  const hex = Array.from(bytes, (byte) => byte.toString(16).padStart(2, "0")).join("");
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
}

function updateRecord(idempotencyKey: string, change: (record: OperationRecord) => OperationRecord) {
  const records = readRecords();
  const index = records.findIndex((record) => record.idempotency_key === idempotencyKey);
  if (index < 0) return null;
  const next = change(records[index]);
  records[index] = next;
  writeRecords(records);
  return next;
}

export function beginOperation(kind: RecoverableOperationKind, request: OperationRecord["request"]): OperationRecord {
  const digest = fingerprint(request);
  const now = new Date().toISOString();
  const record: OperationRecord = {
    schema_version: 1,
    idempotency_key: newKey(),
    kind,
    request: JSON.parse(JSON.stringify(request)) as OperationRecord["request"],
    request_digest: digest,
    job_path: null,
    state: "submitting",
    last_known_job_state: null,
    last_read_at: null,
    created_at: now,
    updated_at: now,
  };
  writeRecords([...readRecords(), record]);
  return record;
}

export function findUnknownOperation(kind: RecoverableOperationKind, route: string): OperationRecord | null {
  return readRecords()
    .reverse()
    .find((record) => record.kind === kind && record.request.route === route && record.state === "unknown") ?? null;
}

export function markOperationUnknown(idempotencyKey: string) {
  return updateRecord(idempotencyKey, (record) => ({
    ...record,
    state: "unknown",
    updated_at: new Date().toISOString(),
  }));
}

export function markOperationRecovering(idempotencyKey: string) {
  return updateRecord(idempotencyKey, (record) => ({
    ...record,
    state: "recovering",
    updated_at: new Date().toISOString(),
  }));
}

export function markOperationAccepted(idempotencyKey: string, jobPath: string) {
  return updateRecord(idempotencyKey, (record) => ({
    ...record,
    job_path: jobPath,
    state: "accepted",
    updated_at: new Date().toISOString(),
  }));
}

export function recordJobObservation(jobPath: string, state: string) {
  const records = readRecords();
  const now = new Date().toISOString();
  let changed = false;
  const next = records.map((record) => {
    if (record.job_path !== jobPath) return record;
    changed = true;
    return { ...record, last_known_job_state: state, last_read_at: now, updated_at: now };
  });
  if (changed) writeRecords(next);
}
