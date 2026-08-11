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
          generation: { id: "script-1", snapshot_id: "snapshot-1", selected_fact_ids: ["fact-1"], configuration: {}, pattern_key: "problem_solution", pattern_version: "1.0", provider: "deterministic", model: "deterministic-v1", prompt_contract_version: "1.0", input_digest: "a".repeat(64), created_at: "2026-08-10T12:00:00Z" },
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
