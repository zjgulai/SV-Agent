import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { delay, http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import { TestApp } from "../../test/TestApp";
import { server } from "../../test/server";

describe("script versions", () => {
  it("renders after a pending script request resolves", async () => {
    server.use(
      http.get("/api/v1/scripts/script-1", async () => {
        await delay(50);
        return HttpResponse.json({
          generation: { id: "script-1", snapshot_id: "snapshot-1", selected_fact_ids: ["fact-1"], excluded_fact_ids: [], configuration: {}, pattern_key: "problem_solution", pattern_version: "1.0", provider: "deterministic", model: "deterministic-v1", prompt_contract_version: "1.0", input_digest: "a".repeat(64), created_at: "2026-08-10T12:00:00Z" },
          versions: [{
            id: "version-1", generation_id: "script-1", parent_version_id: null, created_at: "2026-08-10T12:00:00Z",
            draft: { target_duration_seconds: 15, language: "en", audience: "buyers", snapshot_id: "snapshot-1", phases: [], shots: [], titles: ["Fact-led draft"], tags: [], shooting_list: [] },
            validation_report: { acceptable: true, findings: [], blocking: [] },
          }],
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

  it("shows field-level version changes", async () => {
    render(<TestApp initialEntries={["/scripts/script-1/compare?left=version-0&right=version-1"]} />);

    expect(screen.getByRole("heading", { name: "版本差异" })).toBeVisible();
    expect(await screen.findByText("titles[0]")).toBeVisible();
    expect(screen.getByText("Original")).toBeVisible();
    expect(screen.getByText("Blocked draft")).toBeVisible();
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

  it("shows a recoverable error when deriving a version fails", async () => {
    server.use(
      http.post("/api/v1/scripts/script-1/versions/version-1/derive", () =>
        HttpResponse.json(
          { detail: "Version could not be created", code: "VERSION_FAILED" },
          { status: 500 },
        ),
      ),
    );
    const user = userEvent.setup();
    render(<TestApp initialEntries={["/scripts/script-1"]} />);

    await user.click(await screen.findByRole("button", { name: "创建版本二" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Version could not be created");
  });

  it("shows a recoverable error when version comparison fails", async () => {
    server.use(
      http.get("/api/v1/scripts/script-1/compare", () =>
        HttpResponse.json(
          { detail: "Versions are unavailable", code: "DIFF_FAILED" },
          { status: 500 },
        ),
      ),
    );
    render(
      <TestApp
        initialEntries={["/scripts/script-1/compare?left=version-0&right=version-1"]}
      />,
    );

    expect(await screen.findByRole("alert")).toHaveTextContent("Versions are unavailable");
  });
});
