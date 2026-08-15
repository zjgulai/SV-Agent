export interface FactBinding {
  shot_index: number;
  fact_id: string;
}

interface FactRebindOperation {
  schema_version: 1;
  script_id: string;
  parent_version_id: string;
  fact_bindings: FactBinding[];
  idempotency_key: string;
}

const STORAGE_KEY = "factframe.fact-rebind-operations.v1";
const MAX_RECORDS = 20;

function storage(): Storage | null {
  try {
    return globalThis.sessionStorage;
  } catch {
    return null;
  }
}

function canonicalBindings(bindings: FactBinding[]) {
  return [...bindings]
    .sort((left, right) => left.shot_index - right.shot_index)
    .map((binding) => ({ shot_index: binding.shot_index, fact_id: binding.fact_id }));
}

function isOperation(value: unknown): value is FactRebindOperation {
  if (!value || typeof value !== "object") return false;
  const record = value as Partial<FactRebindOperation>;
  return record.schema_version === 1
    && typeof record.script_id === "string"
    && typeof record.parent_version_id === "string"
    && typeof record.idempotency_key === "string"
    && Array.isArray(record.fact_bindings)
    && record.fact_bindings.every(
      (binding) => typeof binding?.shot_index === "number" && typeof binding.fact_id === "string",
    );
}

function readOperations(): FactRebindOperation[] {
  const raw = storage()?.getItem(STORAGE_KEY);
  if (!raw) return [];
  try {
    const parsed = JSON.parse(raw) as unknown;
    return Array.isArray(parsed) ? parsed.filter(isOperation) : [];
  } catch {
    return [];
  }
}

function writeOperations(records: FactRebindOperation[]) {
  storage()?.setItem(STORAGE_KEY, JSON.stringify(records.slice(-MAX_RECORDS)));
}

function newKey() {
  if (globalThis.crypto?.randomUUID) return globalThis.crypto.randomUUID();
  return `${Date.now()}-${Math.random()}`;
}

export function latestFactRebindOperation(scriptId: string, parentVersionId: string) {
  return readOperations()
    .reverse()
    .find((record) => record.script_id === scriptId && record.parent_version_id === parentVersionId) ?? null;
}

export function factRebindOperation(
  scriptId: string,
  parentVersionId: string,
  bindings: FactBinding[],
) {
  const factBindings = canonicalBindings(bindings);
  const matching = readOperations()
    .reverse()
    .find(
      (record) => record.script_id === scriptId
        && record.parent_version_id === parentVersionId
        && JSON.stringify(record.fact_bindings) === JSON.stringify(factBindings),
    );
  if (matching) return matching;

  const record: FactRebindOperation = {
    schema_version: 1,
    script_id: scriptId,
    parent_version_id: parentVersionId,
    fact_bindings: factBindings,
    idempotency_key: newKey(),
  };
  writeOperations([...readOperations(), record]);
  return record;
}
