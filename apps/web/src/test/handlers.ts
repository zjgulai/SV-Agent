import { http, HttpResponse } from "msw";

import type { Product } from "../api/client";

const now = "2026-08-10T12:00:00Z";
let product: Product | null = null;
let jobReads = 0;

export function resetFixtureState() {
  product = null;
  jobReads = 0;
}

function fixture(title = "Pulse Mix", description = "Resealable drink mix pouch"): Product {
  return {
    product_id: "product-1",
    snapshot: {
      id: "snapshot-1",
      source_id: "product-1",
      title,
      description,
      category_path: [],
      images: [],
      price_amount: null,
      price_currency: null,
      canonical_digest: "a".repeat(64),
      created_at: now,
    },
    facts: [
      {
        id: "fact-1",
        snapshot_id: "snapshot-1",
        claim_type: "description",
        claim: description,
        value: { description },
        evidence_kind: "user_assertion",
        evidence_locator: "manual-form",
        evidence_excerpt: description,
        confidence: "1.0000",
        status: "proposed",
        updated_at: now,
      },
    ],
  };
}

export const handlers = [
  http.get("/api/v1/products", () => HttpResponse.json(product ? [product] : [])),
  http.post("/api/v1/products", async ({ request }) => {
    const body = (await request.json()) as { title: string; description: string };
    product = fixture(body.title, body.description);
    return HttpResponse.json(product, { status: 201 });
  }),
  http.get("/api/v1/products/:id", ({ params }) => {
    const current = product ?? fixture();
    return params.id === current.product_id
      ? HttpResponse.json(current)
      : HttpResponse.json({ detail: "商品不存在" }, { status: 404 });
  }),
  http.patch("/api/v1/products/:productId/facts/:factId", async ({ request }) => {
    const body = (await request.json()) as { status: Product["facts"][number]["status"] };
    product = product ?? fixture();
    product = { ...product, facts: product.facts.map((fact) => ({ ...fact, status: body.status })) };
    return HttpResponse.json(product.facts[0]);
  }),
  http.post("/api/v1/product-imports", () =>
    HttpResponse.json({ id: "import-job-1", state: "queued", source_id: "source-1" }, { status: 202 }),
  ),
  http.get("/api/v1/jobs/:id", () => {
    jobReads += 1;
    return HttpResponse.json(
      jobReads === 1
        ? { id: "job-1", job_type: "script_generation", state: "queued", attempt_count: 0, error_code: null, error_detail: null, result_id: "script-1" }
        : { id: "job-1", job_type: "script_generation", state: "validation_failed", attempt_count: 1, error_code: "SCRIPT_VALIDATION_FAILED", error_detail: "脚本包含无证据声明", result_id: "script-1" },
    );
  }),
  http.get("/api/v1/creative-patterns", () =>
    HttpResponse.json([{ key: "problem_solution", version: "1.0", name: "Problem / Solution", supported_durations: [15, 30, 45] }]),
  ),
  http.post("/api/v1/products/:id/script-generations", () =>
    HttpResponse.json({ id: "job-1", job_type: "script_generation", state: "queued", attempt_count: 0, error_code: null, error_detail: null, result_id: "script-1" }, { status: 202 }),
  ),
  http.get("/api/v1/scripts/script-1", () =>
    HttpResponse.json({
      generation: { id: "script-1", snapshot_id: "snapshot-1", selected_fact_ids: ["fact-1"], excluded_fact_ids: [], configuration: { target_duration_seconds: 15, language: "en", audience: "buyers" }, pattern_key: "problem_solution", pattern_version: "1.0", provider: "deterministic", model: "deterministic-v1", prompt_contract_version: "1.0", input_digest: "a".repeat(64), created_at: now },
      versions: [{
        id: "version-1", generation_id: "script-1", parent_version_id: null, created_at: now,
        draft: { target_duration_seconds: 15, language: "en", audience: "buyers", snapshot_id: "snapshot-1", phases: [{ key: "hook", purpose: "Hook", start_seconds: 0, end_seconds: 15 }], shots: [{ start_seconds: 0, end_seconds: 15, phase_key: "hook", voiceover: "This guarantees results.", visual: "Show product", action: "Hold product", caption: "", acceptance_shot: "Product visible", supported_fact_ids: ["fact-1"], product_claims: ["Resealable pouch"] }], titles: ["Blocked draft"], tags: ["demo"], shooting_list: ["product"] },
        validation_report: { acceptable: false, findings: [{ rule_id: "CLAIM_GUARANTEE", path: "shots[0].voiceover", message: "prohibited claim detected", severity: "blocking", evidence: "guarantees" }], blocking: [{ rule_id: "CLAIM_GUARANTEE", path: "shots[0].voiceover", message: "prohibited claim detected", severity: "blocking", evidence: "guarantees" }] },
      }],
    }),
  ),
  http.get("/api/v1/scripts/:scriptId/versions/:versionId/storyboard-preflight", ({ params }) =>
    HttpResponse.json({
      status: "blocked",
      script_id: params.scriptId,
      version_id: params.versionId,
      snapshot_id: "snapshot-1",
      pattern_key: "problem_solution",
      input_digest: "a".repeat(64),
      selected_facts: [{ id: "fact-1", claim_type: "description", claim: "Resealable drink mix pouch", evidence_kind: "user_assertion", evidence_excerpt: "Resealable drink mix pouch", status: "locked" }],
      excluded_facts: [],
      phases: [{ key: "hook", purpose: "Hook", start_seconds: 0, end_seconds: 15 }],
      shots: [{ start_seconds: 0, end_seconds: 15, phase_key: "hook", voiceover: "This guarantees results.", visual: "Show product", action: "Hold product", caption: "", acceptance_shot: "Product visible", supported_fact_ids: ["fact-1"], product_claims: ["Resealable pouch"] }],
      validation_report: { acceptable: false, findings: [{ rule_id: "CLAIM_GUARANTEE", path: "shots[0].voiceover", message: "prohibited claim detected", severity: "blocking", evidence: "guarantees" }], blocking: [{ rule_id: "CLAIM_GUARANTEE", path: "shots[0].voiceover", message: "prohibited claim detected", severity: "blocking", evidence: "guarantees" }] },
    }),
  ),
  http.get("/api/v1/scripts/script-1/compare", () =>
    HttpResponse.json({ added: [], removed: [], changed: [{ path: "titles[0]", left: "Original", right: "Blocked draft" }] }),
  ),
];
