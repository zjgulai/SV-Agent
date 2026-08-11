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

export class ApiProblem extends Error {
  constructor(public readonly problem: ProblemDetails) {
    super(problem.detail);
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

export interface CreativePattern {
  key: string;
  version: string;
  name: string;
  supported_durations: number[];
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
  voiceover: string;
  visual: string;
  action: string;
  caption: string;
  acceptance_shot: string;
  supported_fact_ids: string[];
  product_claims: string[];
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
}

export interface VersionDiff {
  added: Array<{ path: string; value: unknown }>;
  removed: Array<{ path: string; value: unknown }>;
  changed: Array<{ path: string; left: unknown; right: unknown }>;
}

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
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
  return (await response.json()) as T;
}

export const api = {
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
      audience: string;
      creative_pattern_key: string;
    },
    idempotencyKey: string,
  ) =>
    request<Job>(`/api/v1/products/${productId}/script-generations`, {
      method: "POST",
      headers: { "Idempotency-Key": idempotencyKey },
      body: JSON.stringify(input),
    }),
  getJob: (id: string) => request<Job>(`/api/v1/jobs/${id}`),
  getPatterns: () => request<CreativePattern[]>("/api/v1/creative-patterns"),
  getScript: (id: string) => request<ScriptResource>(`/api/v1/scripts/${id}`),
  deriveVersion: (scriptId: string, versionId: string, title: string) =>
    request<ScriptVersion>(`/api/v1/scripts/${scriptId}/versions/${versionId}/derive`, {
      method: "POST",
      body: JSON.stringify({ title }),
    }),
  compareVersions: (id: string, left: string, right: string) =>
    request<VersionDiff>(`/api/v1/scripts/${id}/compare?left=${encodeURIComponent(left)}&right=${encodeURIComponent(right)}`),
};
