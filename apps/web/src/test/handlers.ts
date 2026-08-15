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

const problemSolutionPlans = {
  15: {
    phases: [["hook", "problem"], ["solution", "demo"], ["cta", "cta"]],
    shots: [["hook", "problem", 2], ["solution", "demo", 4], ["solution", "result", 5], ["cta", "cta", 4]],
  },
  30: {
    phases: [["hook", "problem"], ["problem", "problem"], ["solution", "demo"], ["cta", "cta"]],
    shots: [["hook", "problem", 3], ["problem", "problem", 5], ["problem", "demo", 5], ["solution", "demo", 6], ["solution", "result", 6], ["cta", "cta", 5]],
  },
  45: {
    phases: [["hook", "problem"], ["problem", "problem"], ["solution", "demo"], ["proof", "proof"], ["cta", "cta"]],
    shots: [["hook", "problem", 4], ["problem", "problem", 5], ["problem", "demo", 6], ["solution", "demo", 7], ["solution", "result", 7], ["proof", "proof", 6], ["proof", "detail", 5], ["cta", "cta", 5]],
  },
} as const;

function problemSolutionContract(
  duration_seconds: 15 | 30 | 45,
  language: "en" | "zh-CN",
  unit: "words_per_second" | "han_characters_per_second",
  max: number,
) {
  const plan = problemSolutionPlans[duration_seconds];
  return {
    contract_version: "p1.3b" as const,
    key: "problem_solution",
    version: "1.2",
    name: "Problem / Solution",
    hook_type: "pain",
    duration_seconds,
    language,
    phases: plan.phases.map(([key, shot_role]) => ({ key, purpose: key[0].toUpperCase() + key.slice(1), shot_role, fact_role: "required_selected" as const })),
    shots: plan.shots.map(([phase_key, role, budget_weight]) => ({ phase_key, role, budget_weight, fact_role: "required_selected" as const })),
    speaking_rate: { unit, max },
    field_policy: { fact_bound: ["voiceover", "caption", "product_claims", "supported_fact_ids"], server_owned: ["phase.purpose", "visual", "action", "acceptance_shot", "titles", "tags", "shooting_list"] },
    cta_policy: { mode: "server_generic_no_offer" as const },
    audience_policy: { mode: "record_only" as const, allowed_slots: [] as [] },
    acceptance_checks: ["phase_order", "shot_plan", "timeline_budget", "speaking_rate", "fact_binding", "excluded_deny_set", "server_owned_copy"],
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
  http.get("/api/v1/jobs/:id/events", () =>
    HttpResponse.json([
      { id: "event-1", event_type: "job_created", from_state: null, to_state: "queued", attempt_count: 0, error_code: null, error_detail: null, event_sequence: 1, created_at: now },
    ]),
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
    HttpResponse.json([{
      key: "problem_solution",
      version: "1.2",
      name: "Problem / Solution",
      supported_durations: [15, 30, 45],
      supported_languages: ["en", "zh-CN"],
      contracts: [15, 30, 45].flatMap((duration_seconds) => [
        { language: "en", unit: "words_per_second", max: 2.5 },
        { language: "zh-CN", unit: "han_characters_per_second", max: 4 },
      ].map(({ language, unit, max }) => problemSolutionContract(
        duration_seconds as 15 | 30 | 45,
        language as "en" | "zh-CN",
        unit as "words_per_second" | "han_characters_per_second",
        max,
      ))),
    }]),
  ),
  http.post("/api/v1/products/:id/script-generations", () =>
    HttpResponse.json({ id: "job-1", job_type: "script_generation", state: "queued", attempt_count: 0, error_code: null, error_detail: null, result_id: "script-1" }, { status: 202 }),
  ),
  http.get("/api/v1/scripts/script-1", () =>
    HttpResponse.json({
      generation: { id: "script-1", snapshot_id: "snapshot-1", selected_fact_ids: ["fact-1"], excluded_fact_ids: [], configuration: { target_duration_seconds: 15, language: "en", audience: "buyers" }, pattern_key: "problem_solution", pattern_version: "1.0", provider: "deterministic", model: "deterministic-v1", prompt_contract_version: "1.0", input_digest: "a".repeat(64), created_at: now },
      versions: [{
        id: "version-1", generation_id: "script-1", parent_version_id: null, revision_kind: null, actor_kind: null, reason_code: null, operation_input_digest: null, created_at: now,
        draft: { target_duration_seconds: 15, language: "en", audience: "buyers", snapshot_id: "snapshot-1", phases: [{ key: "hook", purpose: "Hook", start_seconds: 0, end_seconds: 15 }], shots: [{ start_seconds: 0, end_seconds: 15, phase_key: "hook", voiceover: "This guarantees results.", visual: "Show product", action: "Hold product", caption: "", acceptance_shot: "Product visible", supported_fact_ids: ["fact-1"], product_claims: ["Resealable pouch"] }], titles: ["Blocked draft"], tags: ["demo"], shooting_list: ["product"] },
        validation_report: { acceptable: false, findings: [{ rule_id: "CLAIM_GUARANTEE", path: "shots[0].voiceover", message: "prohibited claim detected", severity: "blocking", evidence: "guarantees" }], blocking: [{ rule_id: "CLAIM_GUARANTEE", path: "shots[0].voiceover", message: "prohibited claim detected", severity: "blocking", evidence: "guarantees" }] },
      }],
      fact_contract: { selected: [{ id: "fact-1", claim: "Resealable drink mix pouch", status: "locked", snapshot_id: "snapshot-1" }], excluded: [] },
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
