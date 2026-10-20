import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { delay, http, HttpResponse } from "msw";
import { describe, expect, it, vi } from "vitest";

import { TestApp } from "../../test/TestApp";
import { server } from "../../test/server";

function rebindableScript() {
  const draft = {
    target_duration_seconds: 15,
    language: "en",
    audience: "buyers",
    snapshot_id: "snapshot-1",
    phases: [{ key: "hook", purpose: "Hook", start_seconds: 0, end_seconds: 15 }],
    shots: [{ start_seconds: 0, end_seconds: 15, phase_key: "hook", voiceover: "Resealable drink mix pouch", visual: "Show the pouch", action: "Hold the pouch", caption: "Resealable drink mix pouch", acceptance_shot: "Product visible", supported_fact_ids: ["fact-1"], product_claims: ["Resealable drink mix pouch"] }],
    titles: ["Fact-led draft"],
    tags: ["demo"],
    shooting_list: ["Product visible"],
  };
  return {
    generation: { id: "script-1", snapshot_id: "snapshot-1", selected_fact_ids: ["fact-1", "fact-2"], excluded_fact_ids: [], configuration: {}, pattern_key: "problem_solution", pattern_version: "1.0", provider: "deterministic", model: "deterministic-v1", prompt_contract_version: "1.0", input_digest: "a".repeat(64), created_at: "2026-08-10T12:00:00Z" },
    versions: [{ id: "version-1", generation_id: "script-1", parent_version_id: null, revision_kind: null, actor_kind: null, reason_code: null, operation_input_digest: null, created_at: "2026-08-10T12:00:00Z", draft, validation_report: { acceptable: true, findings: [], blocking: [] } }],
    fact_contract: { selected: [{ id: "fact-1", claim: "Resealable drink mix pouch", status: "locked", snapshot_id: "snapshot-1" }, { id: "fact-2", claim: "Single-serve packet", status: "confirmed", snapshot_id: "snapshot-1" }], excluded: [] },
  };
}

function creativeComparisonFixture() {
  const script = rebindableScript();
  const control = script.versions[0];
  const variant = {
    ...control,
    id: "version-2",
    parent_version_id: control.id,
    draft: { ...control.draft, titles: ["A relief-first hook"] },
    validation_report: {
      acceptable: false,
      findings: [{ rule_id: "CREATIVE_FIELD_UNTRUSTED", path: "titles[0]", message: "server-owned creative field changed", severity: "blocking", evidence: null }],
      blocking: [{ rule_id: "CREATIVE_FIELD_UNTRUSTED", path: "titles[0]", message: "server-owned creative field changed", severity: "blocking", evidence: null }],
    },
  };
  const evidenceNeeds = [
    { code: "COMPARISON_CONTRACT_UNAVAILABLE", context: "comparability", path: null, message: "Single-variable comparability is unverified without an immutable contract." },
    { code: "PERFORMANCE_EVIDENCE_UNAVAILABLE", context: "performance", path: null, message: "No approved performance evidence package is connected." },
    { code: "EXPERIMENT_EVIDENCE_UNAVAILABLE", context: "experiment", path: null, message: "No approved experiment evidence package is connected." },
    { code: "ASSET_EVIDENCE_UNAVAILABLE", context: "asset", path: null, message: "No approved asset evidence package is connected." },
  ];
  return {
    schema_version: "creative-comparison-view-v1",
    script_id: "script-1",
    observed_at: "2026-08-30T12:00:00Z",
    readiness: {
      state: "blocked",
      disposition: "revise",
      single_variable_status: "unverified",
      blockers: [{ code: "CREATIVE_FIELD_UNTRUSTED", context: "script_validation", path: "variant.titles[0]", message: "server-owned creative field changed" }],
      evidence_needs: evidenceNeeds,
    },
    control: { version_id: control.id, parent_version_id: null, created_at: control.created_at, draft: control.draft, stored_validation_report: control.validation_report, live_validation_report: control.validation_report, storyboard_readiness: "ready" },
    variant: { version_id: variant.id, parent_version_id: control.id, created_at: variant.created_at, draft: variant.draft, stored_validation_report: control.validation_report, live_validation_report: variant.validation_report, storyboard_readiness: "blocked" },
    differences: [{ section: "script", path: "titles[0]", change: "changed", kind: "unexpected_change", control_present: true, variant_present: true, control: "Fact-led draft", variant: "A relief-first hook" }],
    product_truth_gate: { status: "pass", snapshot_id: "snapshot-1", pattern_key: "problem_solution", pattern_version: "1.0", selected_facts: script.fact_contract.selected.map((item) => ({ id: item.id, availability: "present", claim: item.claim, status: item.status })), excluded_facts: [] },
    performance_evidence: { availability: "unavailable", source_reference: "docs/research/leap/public-report-evidence.md", limitation: "No approved machine-readable performance evidence package is connected." },
    experiment_evidence: { availability: "unavailable", source_reference: "docs/research/oumomo/evidence-index.md", limitation: "No approved experiment manifest is connected to this comparison." },
    asset_evidence: { availability: "unavailable", source_reference: "tools/momcozy_assets/README.md", limitation: "No approved Asset Bundle or Commercial Approval is connected." },
    limitations: evidenceNeeds,
    projection_digest: "f".repeat(64),
  };
}

describe("script versions", () => {
  it("renders after a pending script request resolves", async () => {
    server.use(
      http.get("/api/v1/scripts/script-1", async () => {
        await delay(50);
        return HttpResponse.json({
          generation: { id: "script-1", snapshot_id: "snapshot-1", selected_fact_ids: ["fact-1"], excluded_fact_ids: [], configuration: {}, pattern_key: "problem_solution", pattern_version: "1.0", provider: "deterministic", model: "deterministic-v1", prompt_contract_version: "1.0", input_digest: "a".repeat(64), created_at: "2026-08-10T12:00:00Z" },
          versions: [{
            id: "version-1", generation_id: "script-1", parent_version_id: null, revision_kind: null, actor_kind: null, reason_code: null, operation_input_digest: null, created_at: "2026-08-10T12:00:00Z",
            draft: { target_duration_seconds: 15, language: "en", audience: "buyers", snapshot_id: "snapshot-1", phases: [], shots: [], titles: ["Fact-led draft"], tags: [], shooting_list: [] },
            validation_report: { acceptable: true, findings: [], blocking: [] },
          }],
          fact_contract: { selected: [{ id: "fact-1", claim: "Resealable drink mix pouch", status: "locked", snapshot_id: "snapshot-1" }], excluded: [] },
        });
      }),
    );

    render(<TestApp initialEntries={["/scripts/script-1"]} />);

    expect(screen.getByText("正在读取脚本版本…")).toBeVisible();
    expect(await screen.findByRole("heading", { name: "结构化脚本" })).toBeVisible();
  });

  it("shows blocking findings before the structured timeline", async () => {
    render(<TestApp initialEntries={["/scripts/script-1"]} />);

    expect(await screen.findByRole("heading", { name: "结构化脚本" })).toBeVisible();
    expect(screen.getByText("校验未通过")).toBeVisible();
    expect(screen.getByText("CLAIM_GUARANTEE")).toBeVisible();
    expect(screen.getByText("This guarantees results.")).toBeVisible();
    expect(screen.getByRole("link", { name: "导出 Markdown" })).toHaveAttribute(
      "href",
      "/api/v1/scripts/script-1/versions/version-1/export?format=markdown",
    );
  });

  it("renders the read-only creative comparison from one production projection", async () => {
    let reads = 0;
    server.use(
      http.get("/api/v1/scripts/script-1/creative-comparison", ({ request }) => {
        reads += 1;
        const url = new URL(request.url);
        expect(url.searchParams.get("control")).toBe("version-1");
        expect(url.searchParams.get("variant")).toBe("version-2");
        return HttpResponse.json(creativeComparisonFixture());
      }),
    );
    render(<TestApp initialEntries={["/scripts/script-1/compare?left=version-1&right=version-2"]} />);

    expect(await screen.findByRole("heading", { name: "创意对比实验台" })).toBeVisible();
    const statuses = await screen.findByLabelText("对比状态");
    expect(within(statuses).getByText("BLOCKED")).toBeVisible();
    expect(within(statuses).getByText("NEEDS EVIDENCE")).toBeVisible();
    expect(screen.getByText("Single variable · unverified")).toBeVisible();
    expect(screen.getByRole("heading", { name: "Control" })).toBeVisible();
    expect(screen.getByRole("heading", { name: "Variant" })).toBeVisible();
    expect(screen.getByText("version-1")).toBeVisible();
    expect(screen.getByText("version-2")).toBeVisible();
    expect(await screen.findByText("titles[0]")).toBeVisible();
    expect(screen.getAllByText("UNAVAILABLE")).toHaveLength(3);
    expect(screen.getByText("Product Truth")).toBeVisible();
    expect(screen.getByLabelText("当前证据限制")).toBeVisible();
    expect(screen.queryByText(/fixture-v1/i)).not.toBeInTheDocument();
    expect(screen.queryByLabelText("原型版本切换器")).not.toBeInTheDocument();
    expect(reads).toBe(1);
  });

  it("switches comparison lenses without another API request", async () => {
    let reads = 0;
    server.use(
      http.get("/api/v1/scripts/script-1/creative-comparison", () => {
        reads += 1;
        return HttpResponse.json(creativeComparisonFixture());
      }),
    );
    const user = userEvent.setup();
    render(<TestApp initialEntries={["/scripts/script-1/compare?left=version-1&right=version-2"]} />);

    expect(await screen.findByRole("heading", { name: "Control" })).toBeVisible();
    await user.click(screen.getByRole("button", { name: "Storyboard" }));
    expect(screen.getByText("Control storyboard preflight · READY")).toBeVisible();
    await user.click(screen.getByRole("button", { name: "Asset" }));
    expect(screen.getByText("Asset evidence · UNAVAILABLE")).toBeVisible();
    expect(reads).toBe(1);
  });

  it("keeps a blocked storyboard preflight out of rendering", async () => {
    render(<TestApp initialEntries={["/scripts/script-1/versions/version-1/storyboard-preflight"]} />);

    expect(await screen.findByRole("heading", { name: "事实约束分镜预检" })).toBeVisible();
    expect(screen.getByText("当前版本不可进入渲染")).toBeVisible();
    expect(screen.getByText("CLAIM_GUARANTEE")).toBeVisible();
    expect(screen.queryByText("进入渲染")).not.toBeInTheDocument();
  });

  it("freezes a ready storyboard and approves its zero-cost preview", async () => {
    let approvalStatus: "unreviewed" | "approved" = "unreviewed";
    const draft = {
      target_duration_seconds: 15,
      language: "en",
      audience: "buyers",
      snapshot_id: "snapshot-1",
      phases: [{ key: "hook", purpose: "Hook", start_seconds: 0, end_seconds: 15 }],
      shots: [{ start_seconds: 0, end_seconds: 15, phase_key: "hook", voiceover: "Resealable drink mix pouch", visual: "Show the pouch", action: "Hold the pouch", caption: "Resealable drink mix pouch", acceptance_shot: "Product visible", supported_fact_ids: ["fact-1"], product_claims: ["Resealable drink mix pouch"] }],
      titles: ["Fact-led draft"], tags: ["demo"], shooting_list: ["Product visible"],
    };
    const validation = { acceptable: true, findings: [], blocking: [] };
    const storyboard = {
      id: "storyboard-1", script_version_id: "version-1", snapshot_id: "snapshot-1",
      selected_fact_ids: ["fact-1"], excluded_fact_ids: [], pattern_key: "problem_solution", pattern_version: "1.0", phase_sequence: ["hook"], draft, validation_report: validation,
      preflight_digest: "a".repeat(64), storyboard_digest: "b".repeat(64), preview_contract_version: "p2.0-animatic-v1", created_at: "2026-08-10T12:00:00Z",
    };
    server.use(
      http.get("/api/v1/scripts/script-1/versions/version-1/storyboard-preflight", () => HttpResponse.json({
        status: "ready", script_id: "script-1", version_id: "version-1", snapshot_id: "snapshot-1", pattern_key: "problem_solution", input_digest: "a".repeat(64),
        selected_facts: [{ id: "fact-1", claim_type: "description", claim: "Resealable drink mix pouch", evidence_kind: "user_assertion", evidence_excerpt: "Resealable drink mix pouch", status: "locked" }], excluded_facts: [], phases: draft.phases, shots: draft.shots, validation_report: validation,
      })),
      http.post("/api/v1/scripts/script-1/versions/version-1/storyboards", () => HttpResponse.json(storyboard, { status: 201 })),
      http.get("/api/v1/storyboards/storyboard-1", () => HttpResponse.json(storyboard)),
      http.get("/api/v1/storyboards/storyboard-1/preview", () => HttpResponse.json({ storyboard_id: "storyboard-1", storyboard_digest: storyboard.storyboard_digest, preview_digest: "c".repeat(64), preview_contract_version: "p2.0-animatic-v1", image_indexes: [0], shots: [{ index: 1, ...draft.shots[0] }] })),
      http.get("/api/v1/storyboards/storyboard-1/approval", () => HttpResponse.json(approvalStatus === "approved" ? { status: "approved", latest_event: { id: "approval-1", storyboard_id: "storyboard-1", decision: "approved", reason: null, storyboard_digest: storyboard.storyboard_digest, preflight_digest: storyboard.preflight_digest, approval_digest: "d".repeat(64), validation_report: validation, event_sequence: 1, created_at: "2026-08-10T12:00:00Z" } } : { status: "unreviewed", latest_event: null })),
      http.post("/api/v1/storyboards/storyboard-1/approval-events", () => {
        approvalStatus = "approved";
        return HttpResponse.json({ id: "approval-1", storyboard_id: "storyboard-1", decision: "approved", reason: null, storyboard_digest: storyboard.storyboard_digest, preflight_digest: storyboard.preflight_digest, approval_digest: "d".repeat(64), validation_report: validation, event_sequence: 1, created_at: "2026-08-10T12:00:00Z" }, { status: 201 });
      }),
    );
    const user = userEvent.setup();
    render(<TestApp initialEntries={["/scripts/script-1/versions/version-1/storyboard-preflight"]} />);

    await user.click(await screen.findByRole("button", { name: "创建审核版分镜" }));
    expect(await screen.findByRole("heading", { name: "审核版分镜" })).toBeVisible();
    expect(screen.getByLabelText("零成本 animatic 预览")).toBeVisible();
    expect(screen.getByText("图片引用 · 1")).toBeVisible();
    expect(screen.queryByText("生成视频")).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "批准" }));
    expect(await screen.findByText("已批准用于未来报价门禁")).toBeVisible();
  });

  it("sends only frozen fact bindings when creating a rebind version", async () => {
    let received: { body: unknown; key: string | null } | null = null;
    const script = rebindableScript();
    server.use(
      http.get("/api/v1/scripts/script-1", () => HttpResponse.json(script)),
      http.post("/api/v1/scripts/script-1/versions/version-1/derive", async ({ request }) => {
        received = { body: await request.json(), key: request.headers.get("Idempotency-Key") };
        return HttpResponse.json({ ...script.versions[0], id: "version-2", parent_version_id: "version-1", revision_kind: "fact_rebind", actor_kind: "local_operator", reason_code: "fact_rebind", operation_input_digest: "b".repeat(64) }, { status: 201 });
      }),
    );
    const user = userEvent.setup();
    render(<TestApp initialEntries={["/scripts/script-1"]} />);

    await user.selectOptions(await screen.findByLabelText("分镜 1 绑定事实"), "fact-2");
    await user.click(screen.getByRole("button", { name: "保存事实重绑版本" }));

    expect(received).toEqual({ body: { fact_bindings: [{ shot_index: 0, fact_id: "fact-2" }] }, key: expect.any(String) });
  });

  it("shows a recoverable error when fact-bound version creation fails", async () => {
    server.use(
      http.get("/api/v1/scripts/script-1", () => HttpResponse.json(rebindableScript())),
      http.post("/api/v1/scripts/script-1/versions/version-1/derive", () =>
        HttpResponse.json(
          { detail: "Version could not be created", code: "VERSION_FAILED" },
          { status: 500 },
        ),
      ),
    );
    const user = userEvent.setup();
    render(<TestApp initialEntries={["/scripts/script-1"]} />);

    await user.click(await screen.findByRole("button", { name: "保存事实重绑版本" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Version could not be created");
  });

  it("fails closed without retrying an integrity error", async () => {
    server.use(
      http.get("/api/v1/scripts/script-1/creative-comparison", () =>
        HttpResponse.json(
          { detail: "Versions are unavailable", code: "DIFF_FAILED" },
          { status: 500 },
        ),
      ),
    );
    render(
      <TestApp
        initialEntries={["/scripts/script-1/compare?left=version-1&right=version-2"]}
      />,
    );

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("事实完整性校验失败");
    expect(alert).toHaveTextContent("Versions are unavailable");
    expect(screen.queryByRole("button", { name: "重试" })).not.toBeInTheDocument();
  });

  it("offers retry only when product truth is temporarily unavailable", async () => {
    server.use(
      http.get("/api/v1/scripts/script-1/creative-comparison", () =>
        HttpResponse.json(
          { detail: "Product truth is temporarily unavailable", code: "PRODUCT_TRUTH_UNAVAILABLE" },
          { status: 503 },
        ),
      ),
    );
    render(
      <TestApp
        initialEntries={["/scripts/script-1/compare?left=version-1&right=version-2"]}
      />,
    );

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("暂时无法读取权威事实");
    expect(screen.getByRole("button", { name: "重试" })).toBeVisible();
  });

  it("restores the complete legacy diff when the rollout flag is disabled", async () => {
    vi.stubEnv("VITE_CREATIVE_COMPARISON_LAB", "false");
    server.use(
      http.get("/api/v1/scripts/script-1/compare", () => HttpResponse.json({
        changed: [{ path: "titles[0]", left: "Original", right: "Revised" }],
        added: [],
        removed: [],
      })),
    );
    try {
      render(
        <TestApp
          initialEntries={["/scripts/script-1/compare?left=version-1&right=version-2"]}
        />,
      );

      expect(await screen.findByRole("heading", { name: "版本差异" })).toBeVisible();
      expect(await screen.findByText("titles[0]")).toBeVisible();
      expect(screen.getByText("Original")).toBeVisible();
      expect(screen.getByText("Revised")).toBeVisible();
    } finally {
      vi.unstubAllEnvs();
    }
  });
});
