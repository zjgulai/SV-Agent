import { render, screen, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import { TestApp } from "../../test/TestApp";
import { server } from "../../test/server";
import {
  readBrowserTaskDrafts,
  readBrowserTaskDraftsFrom,
} from "../../features/sv-agent/state/browserTaskDrafts";


describe("SV-Agent Task and Decision Inbox", () => {
  it("shows persisted Tasks with their authority and ordering reason", async () => {
    server.use(
      http.get("/api/v1/sv-agent/tasks", () =>
        HttpResponse.json({
          schema_version: "sv-task-inbox/v1",
          authority: "postgresql",
          ordering_policy_version: "sv-task-inbox-order/v1",
          items: [
            {
              task_id: "24000000-0000-0000-0000-000000000001",
              task_revision: 1,
              goal_track: "brand_voice_social_resonance",
              subject: "Momcozy baby reaction story",
              decision_question: "Which baby story should be tested next?",
              active_run_id: "25000000-0000-0000-0000-000000000001",
              active_run_revision: 2,
              run_state: "awaiting_approval",
              pending_decision_count: 1,
              pending_gate_kinds: ["replication_contract"],
              lane: "needs_decision",
              ordering_reason: "human_decision_required",
              priority_at: "2026-10-21T12:00:00Z",
            },
          ],
          truncated: false,
        }),
      ),
    );

    render(<TestApp initialEntries={["/sv-agent/tasks"]} />);

    expect(
      await screen.findByRole("heading", { name: "Task 与决定收件箱" }),
    ).toBeVisible();
    const persisted = screen.getByRole("region", { name: "已保存的 Task" });
    expect(within(persisted).getByText("PostgreSQL 权威记录")).toBeVisible();
    expect(
      await within(persisted).findByText("Momcozy baby reaction story"),
    ).toBeVisible();
    expect(within(persisted).getByText("等待你的决定")).toBeVisible();
    expect(within(persisted).getByText(/排序原因：当前有人类决定待处理/)).toBeVisible();
    expect(
      within(persisted).getByRole("link", { name: "打开 Mission Control" }),
    ).toHaveAttribute(
      "href",
      "/sv-agent/tasks/24000000-0000-0000-0000-000000000001",
    );
    expect(screen.queryByRole("button", { name: /render|publish|ship|渲染|发布|交付/i })).toBeNull();
  });

  it("keeps browser-local drafts separate from persisted Tasks", async () => {
    server.use(
      http.get("/api/v1/sv-agent/tasks", () =>
        HttpResponse.json({
          schema_version: "sv-task-inbox/v1",
          authority: "postgresql",
          ordering_policy_version: "sv-task-inbox-order/v1",
          items: [],
          truncated: false,
        }),
      ),
    );
    window.sessionStorage.setItem(
      "sv-agent-task-drafts/v1",
      JSON.stringify({
        schema_version: "sv-task-drafts/v1",
        drafts: [
          {
            draft_id: "draft-local-1",
            subject: "Momcozy bedtime reaction idea",
            decision_question: "Which bedtime moment should the brief explore?",
            updated_at: "2026-10-21T13:00:00Z",
          },
        ],
      }),
    );

    render(<TestApp initialEntries={["/sv-agent/tasks"]} />);

    expect(await screen.findByText("还没有已保存的 Task")).toBeVisible();
    const drafts = screen.getByRole("region", { name: "浏览器本地草稿" });
    expect(within(drafts).getByText("非权威 · 本机")).toBeVisible();
    expect(within(drafts).getByText("Momcozy bedtime reaction idea")).toBeVisible();
    expect(within(drafts).getByText("尚未写入 PostgreSQL")).toBeVisible();
    expect(within(drafts).queryByText(/Task revision|Run ·/)).toBeNull();
  });

  it("keeps the authoritative Inbox usable when browser storage is unavailable", () => {
    const throwingStorage = {
      getItem: () => {
        throw new DOMException("Storage disabled", "SecurityError");
      },
    } as unknown as Storage;

    expect(readBrowserTaskDrafts(throwingStorage)).toEqual({
      drafts: [],
      invalidDraftIgnored: true,
    });
    expect(
      readBrowserTaskDraftsFrom(() => {
        throw new DOMException("Storage blocked", "SecurityError");
      }),
    ).toEqual({ drafts: [], invalidDraftIgnored: true });
  });
});

