import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import { TestApp } from "../../test/TestApp";
import { server } from "../../test/server";

describe("generation jobs", () => {
  it("renders the selected frozen pattern contract without editable creative slots", async () => {
    render(<TestApp initialEntries={["/products/product-1/generate"]} />);

    expect(await screen.findByRole("region", { name: "冻结 Pattern 合同" })).toHaveTextContent(
      "镜头 1 · problem · 必须绑定已选事实 · 13%",
    );
    expect(screen.getByText("受众仅影响服务端场景、道具与拍摄槽")).toBeVisible();
    expect(screen.getByText("CTA 不含优惠")).toBeVisible();
    expect(screen.queryByLabelText(/场景|语气|促销/)).not.toBeInTheDocument();
  });

  it("renders every frozen shot for the 15, 30, and 45 second defaults", async () => {
    const user = userEvent.setup();
    render(<TestApp initialEntries={["/products/product-1/generate"]} />);

    await screen.findByRole("region", { name: "冻结 Pattern 合同" });
    expect(screen.getAllByText(/^镜头 \d+ ·/)).toHaveLength(4);

    await user.selectOptions(screen.getByLabelText("目标时长"), "30");
    expect(screen.getAllByText(/^镜头 \d+ ·/)).toHaveLength(6);

    await user.selectOptions(screen.getByLabelText("目标时长"), "45");
    expect(screen.getAllByText(/^镜头 \d+ ·/)).toHaveLength(8);
  });

  it("shows inactive Promotion Facts as unavailable instead of sending them as fact selections", async () => {
    server.use(
      http.get("/api/v1/products/product-1", () =>
        HttpResponse.json({
          product_id: "product-1",
          snapshot: { id: "snapshot-1", source_id: "product-1", title: "Pulse Mix", description: null, category_path: [], images: [], price_amount: null, price_currency: null, canonical_digest: "a".repeat(64), created_at: "2026-08-12T12:00:00Z" },
          facts: [
            { id: "fact-supported", snapshot_id: "snapshot-1", claim_type: "feature", claim: "Resealable pouch", value: {}, evidence_kind: "user_assertion", evidence_locator: "manual-form", evidence_excerpt: "Supported", confidence: "1", status: "confirmed", updated_at: "2026-08-12T12:00:00Z" },
            { id: "promo-active", snapshot_id: "snapshot-1", claim_type: "promotion", claim: "10% off on TikTok Shop in the US.", value: { effective_from: "2000-01-01T00:00:00-08:00", effective_to: "2100-01-01T00:00:00-08:00" }, evidence_kind: "user_assertion", evidence_locator: "manual-form", evidence_excerpt: "Promotion", confidence: "1", status: "confirmed", updated_at: "2026-08-12T12:00:00Z" },
            { id: "promo-expired", snapshot_id: "snapshot-1", claim_type: "promotion", claim: "Expired offer", value: { effective_from: "2000-01-01T00:00:00-08:00", effective_to: "2001-01-01T00:00:00-08:00" }, evidence_kind: "user_assertion", evidence_locator: "manual-form", evidence_excerpt: "Expired", confidence: "1", status: "confirmed", updated_at: "2026-08-12T12:00:00Z" },
          ],
        }),
      ),
      http.get("/api/v1/creative-patterns", () =>
        HttpResponse.json([{
          key: "offer_cta",
          version: "1.2",
          name: "Offer CTA",
          supported_durations: [15],
          supported_languages: ["en"],
          contracts: [{
            contract_version: "p1.3c",
            key: "offer_cta",
            version: "1.2",
            name: "Offer CTA",
            hook_type: "benefit",
            duration_seconds: 15,
            language: "en",
            phases: ["hook", "solution", "cta"].map((key) => ({ key, purpose: key, shot_role: key, fact_role: "required_selected" })),
            shots: [["hook", "hook", 2], ["solution", "demo", 4], ["solution", "result", 5], ["cta", "cta", 4]].map(([phase_key, role, budget_weight]) => ({ phase_key, role, budget_weight, fact_role: "required_selected" })),
            speaking_rate: { unit: "words_per_second", max: 2.5 },
            field_policy: { fact_bound: ["voiceover"], server_owned: ["visual"] },
            cta_policy: { mode: "server_promotion_final_cta" },
            audience_policy: { mode: "server_owned_profile", allowed_slots: ["scene"] },
            acceptance_checks: ["promotion_final_cta"],
          }],
        }]),
      ),
    );
    const user = userEvent.setup();
    render(<TestApp initialEntries={["/products/product-1/generate"]} />);

    await screen.findByRole("heading", { name: "配置事实脚本" });
    await user.selectOptions(screen.getByLabelText("创意结构"), "offer_cta");
    const promotionSelect = screen.getByRole("combobox", { name: /Promotion Fact/ });
    expect(screen.getByRole("option", { name: "10% off on TikTok Shop in the US." })).toBeEnabled();
    expect(screen.getByRole("option", { name: "Expired offer（当前不可用）" })).toBeDisabled();
    expect(screen.queryByText("Expired offer", { selector: ".fact-selection-row strong" })).not.toBeInTheDocument();
    await user.selectOptions(promotionSelect, "promo-active");
    expect(promotionSelect).toHaveValue("promo-active");
  });

  it("submits an ordered selection with its explicit deny-set", async () => {
    const requests: Array<{ selected_fact_ids: string[]; excluded_fact_ids: string[] }> = [];
    server.use(
      http.get("/api/v1/products/product-1", () =>
        HttpResponse.json({
          product_id: "product-1",
          snapshot: { id: "snapshot-1", source_id: "product-1", title: "Pulse Mix", description: null, category_path: [], images: [], price_amount: null, price_currency: null, canonical_digest: "a".repeat(64), created_at: "2026-08-12T12:00:00Z" },
          facts: [
            { id: "fact-a", snapshot_id: "snapshot-1", claim_type: "feature", claim: "First fact", value: {}, evidence_kind: "user_assertion", evidence_locator: "manual-form", evidence_excerpt: "First", confidence: "1", status: "confirmed", updated_at: "2026-08-12T12:00:00Z" },
            { id: "fact-b", snapshot_id: "snapshot-1", claim_type: "feature", claim: "Second fact", value: {}, evidence_kind: "user_assertion", evidence_locator: "manual-form", evidence_excerpt: "Second", confidence: "1", status: "locked", updated_at: "2026-08-12T12:00:00Z" },
            { id: "fact-c", snapshot_id: "snapshot-1", claim_type: "feature", claim: "Excluded fact", value: {}, evidence_kind: "user_assertion", evidence_locator: "manual-form", evidence_excerpt: "Excluded", confidence: "1", status: "confirmed", updated_at: "2026-08-12T12:00:00Z" },
          ],
        }),
      ),
      http.post("/api/v1/products/product-1/script-generations", async ({ request }) => {
        requests.push(await request.json() as { selected_fact_ids: string[]; excluded_fact_ids: string[] });
        return HttpResponse.json({ id: "job-selection-1", job_type: "script_generation", state: "queued", attempt_count: 0, error_code: null, error_detail: null, result_id: "script-1" }, { status: 202 });
      }),
    );
    const user = userEvent.setup();
    render(<TestApp initialEntries={["/products/product-1/generate"]} />);

    await screen.findByRole("heading", { name: "配置事实脚本" });
    expect(screen.getByRole("button", { name: "创建生成任务" })).toBeDisabled();
    await user.click(screen.getAllByRole("button", { name: "纳入" })[0]);
    await user.click(screen.getAllByRole("button", { name: "纳入" })[1]);
    await user.click(screen.getAllByRole("button", { name: "排除" })[2]);
    await user.click(screen.getByRole("button", { name: "上移 Second fact" }));
    await user.click(screen.getByRole("button", { name: "创建生成任务" }));

    expect(requests).toMatchObject([
      { selected_fact_ids: ["fact-b", "fact-a"], excluded_fact_ids: ["fact-c"] },
    ]);
  });

  it("restores a queued job and stops polling at validation_failed", async () => {
    let reads = 0;
    server.use(
      http.get("/api/v1/jobs/job-1", () => {
        reads += 1;
        return HttpResponse.json(
          reads < 3
            ? { id: "job-1", job_type: "script_generation", state: "queued", attempt_count: 0, error_code: null, error_detail: null, result_id: "script-1" }
            : { id: "job-1", job_type: "script_generation", state: "validation_failed", attempt_count: 1, error_code: "SCRIPT_VALIDATION_FAILED", error_detail: "脚本包含无证据声明", result_id: "script-1" },
        );
      }),
    );
    render(<TestApp initialEntries={["/jobs/job-1"]} />);

    expect(await screen.findByRole("status")).toHaveTextContent("正在生成");
    expect(await screen.findByText("脚本包含无证据声明", {}, { timeout: 2000 })).toBeVisible();
    expect(screen.getByRole("status")).toHaveTextContent("校验未通过");
    expect(await screen.findByLabelText("任务实际阶段")).toHaveTextContent("正在生成");
    expect(screen.getByRole("link", { name: "查看脚本" })).toHaveAttribute(
      "href",
      "/scripts/script-1",
    );
  });

  it("shows a dead-lettered delivery as an operator recovery state", async () => {
    server.use(
      http.get("/api/v1/jobs/:id", () =>
        HttpResponse.json({ id: "job-dead", job_type: "product_import", state: "queued", attempt_count: 0, error_code: null, error_detail: null, result_id: "product-1" }),
      ),
      http.get("/api/v1/jobs/:id/events", () =>
        HttpResponse.json([
          { id: "event-1", event_type: "job_created", from_state: null, to_state: "queued", attempt_count: 0, error_code: null, error_detail: null, event_sequence: 1, created_at: "2026-08-10T12:00:00Z" },
          { id: "event-2", event_type: "dispatch_dead_lettered", from_state: null, to_state: "queued", attempt_count: 0, error_code: "OUTBOX_MAX_DELIVERY_ATTEMPTS", error_detail: "Task broker delivery requires operator recovery.", event_sequence: 2, created_at: "2026-08-10T12:01:00Z" },
        ]),
      ),
    );
    render(<TestApp initialEntries={["/jobs/job-dead"]} />);

    expect(await screen.findByRole("status")).toHaveTextContent("投递暂停");
    expect(screen.getByText("需要运维恢复")).toBeVisible();
    expect(screen.queryByRole("button", { name: /重新投递/ })).not.toBeInTheDocument();
  });

  it("opens the original Job when generation returns malformed JSON with Location", async () => {
    const keys: string[] = [];
    server.use(
      http.get("/api/v1/products/product-1", () =>
        HttpResponse.json({
          product_id: "product-1",
          snapshot: { id: "snapshot-1", source_id: "product-1", title: "Pulse Mix", description: null, category_path: [], images: [], price_amount: null, price_currency: null, canonical_digest: "a".repeat(64), created_at: "2026-08-12T12:00:00Z" },
          facts: [
            { id: "fact-known", snapshot_id: "snapshot-1", claim_type: "feature", claim: "Known fact", value: {}, evidence_kind: "user_assertion", evidence_locator: "manual-form", evidence_excerpt: "Known", confidence: "1", status: "confirmed", updated_at: "2026-08-12T12:00:00Z" },
          ],
        }),
      ),
      http.post("/api/v1/products/product-1/script-generations", ({ request }) => {
        keys.push(request.headers.get("idempotency-key") ?? "");
        return new HttpResponse("not json", {
          status: 202,
          headers: { Location: "/api/v1/jobs/generation-known" },
        });
      }),
      http.get("/api/v1/jobs/generation-known", () =>
        HttpResponse.json({
          id: "generation-known",
          job_type: "script_generation",
          state: "queued",
          attempt_count: 0,
          error_code: null,
          error_detail: null,
          result_id: "script-1",
        }),
      ),
    );
    const user = userEvent.setup();
    render(<TestApp initialEntries={["/products/product-1/generate"]} />);

    await screen.findByRole("heading", { name: "配置事实脚本" });
    await user.click(screen.getAllByRole("button", { name: "纳入" })[0]);
    await user.click(screen.getByRole("button", { name: "创建生成任务" }));

    expect(await screen.findByRole("status")).toHaveTextContent("正在生成");
    expect(keys).toHaveLength(1);
  });
});
