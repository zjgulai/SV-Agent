import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import { TestApp } from "../../test/TestApp";
import { server } from "../../test/server";

describe("generation jobs", () => {
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
    render(<TestApp initialEntries={["/jobs/job-1"]} />);

    expect(await screen.findByText("正在生成")).toBeVisible();
    expect(await screen.findByText("脚本包含无证据声明", {}, { timeout: 2000 })).toBeVisible();
    expect(screen.getByRole("status")).toHaveTextContent("校验未通过");
    expect(screen.getByRole("link", { name: "查看脚本" })).toHaveAttribute(
      "href",
      "/scripts/script-1",
    );
  });
});
