import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import { TestApp } from "../../test/TestApp";
import { server } from "../../test/server";

const taskId = "31000000-0000-0000-0000-000000000001";

const workspace = {
  schema_version: "sv-approval-replay/v1",
  authority: "postgresql",
  task: {
    task_id: taskId,
    task_revision: 3,
    subject: "换尿布反应挑战",
  },
  run: {
    run_id: "31000000-0000-0000-0000-000000000002",
    run_revision: 4,
    state: "awaiting_approval",
  },
  summary: {
    pending: 1,
    decided: 1,
    stale: 1,
  },
  decision_vocabulary: ["approve", "reject", "request_evidence", "stop"],
  decision_available: false,
  approvals: [
    {
      request_version: 2,
      gate_kind: "replication_contract",
      target_artifact_type: "replication_contract",
      target_version: 2,
      decision_state: "pending",
      scope_state: "current",
      predicted_effects: ["effect: allow_next_read_only_stage"],
      explicit_non_effects: ["effect: publish"],
      evidence: ["status: bounded"],
      limitations: ["code: local_review_only"],
      stale_conditions: ["field: artifact_digest"],
      decision: null,
      decided_at: null,
      audit: { task_revision: 3, run_revision: 4 },
    },
    {
      request_version: 2,
      gate_kind: "replication_contract",
      target_artifact_type: "adaptation_package",
      target_version: 1,
      decision_state: "decided",
      scope_state: "stale",
      predicted_effects: ["effect: close_storyboard_review"],
      explicit_non_effects: ["effect: commercial_approval"],
      evidence: ["status: reviewed"],
      limitations: ["code: superseded_scope"],
      stale_conditions: ["field: task_revision"],
      decision: "request_evidence",
      decided_at: "2026-10-21T09:12:00Z",
      audit: { task_revision: 2, run_revision: 3 },
    },
  ],
  approvals_truncated: false,
  timeline: {
    snapshot_through_sequence: 9,
    next_after_sequence: null,
    truncated: false,
    entries: [
      {
        event_sequence: 5,
        kind: "plan_revision",
        event_type: "run.plan_recorded.v1",
        summary: "RunPlan v2 已记录。",
        task_revision: 3,
        run_revision: 4,
      },
      {
        event_sequence: 6,
        kind: "tool_run",
        event_type: "tool_run.completed.v1",
        summary: "只读工具执行完成。",
        task_revision: 3,
        run_revision: 4,
      },
      {
        event_sequence: 7,
        kind: "artifact_revision",
        event_type: "artifact.recorded.v1",
        summary: "replication_contract v2 已记录。",
        task_revision: 3,
        run_revision: 4,
      },
      {
        event_sequence: 8,
        kind: "approval_request",
        event_type: "approval.requested.v1",
        summary: "replication_contract 批准请求 v2 已记录。",
        task_revision: 3,
        run_revision: 4,
      },
      {
        event_sequence: 9,
        kind: "decision",
        event_type: "human_decision.recorded.v1",
        summary: "人工决定 request_evidence 已记录。",
        task_revision: 2,
        run_revision: 3,
      },
    ],
  },
  explicit_non_effects: [
    "does_not_write_postgresql",
    "does_not_decide_approvals",
    "does_not_advance_task_or_run",
    "does_not_call_providers",
    "does_not_render_or_publish",
  ],
} as const;

describe("SV-Agent Approval and Replay", () => {
  it("shows version-bound approval cards and a GET-only factual timeline", async () => {
    const methods: string[] = [];
    server.use(
      http.get("/api/v1/sv-agent/tasks/:taskId/replay", ({ params, request }) => {
        expect(params.taskId).toBe(taskId);
        methods.push(request.method);
        return HttpResponse.json(workspace);
      }),
    );

    const user = userEvent.setup();
    render(<TestApp initialEntries={[`/sv-agent/tasks/${taskId}/approval-replay`]} />);

    expect(
      await screen.findByRole("heading", { name: "换尿布反应挑战的批准与回放" }),
    ).toBeVisible();
    expect(screen.getByText("PostgreSQL 权威投影")).toBeVisible();
    expect(screen.getByText("1 个待决定")).toBeVisible();
    expect(screen.getByText("1 个已记录决定")).toBeVisible();
    expect(screen.getByText("1 个已失效范围")).toBeVisible();

    const approvals = screen.getByRole("region", { name: "批准请求" });
    expect(within(approvals).getByText("复刻合同 · v2")).toBeVisible();
    expect(within(approvals).getByText("品牌适配包 · v1")).toBeVisible();
    expect(within(approvals).getByText("等待人工决定")).toBeVisible();
    expect(within(approvals).getByText("已失效，仅保留历史事实")).toBeVisible();
    expect(within(approvals).getByText("请求补充证据")).toBeVisible();
    expect(within(approvals).getByText("effect: allow_next_read_only_stage")).toBeVisible();
    expect(within(approvals).getByText("effect: publish")).toBeVisible();
    expect(within(approvals).getByText("status: bounded")).toBeVisible();
    expect(within(approvals).getByText("code: local_review_only")).toBeVisible();
    expect(within(approvals).getByText("field: artifact_digest")).toBeVisible();

    expect(screen.queryByRole("button", { name: /批准|拒绝|请求补充证据|停止/ })).toBeNull();
    expect(screen.getByText("本页不会提交任何人工决定。" )).toBeVisible();

    const timeline = screen.getByRole("region", { name: "事实回放" });
    const items = within(timeline).getAllByRole("listitem");
    expect(items).toHaveLength(5);
    expect(items.map((item) => item.textContent)).toEqual([
      expect.stringContaining("RunPlan v2 已记录。"),
      expect.stringContaining("只读工具执行完成。"),
      expect.stringContaining("replication_contract v2 已记录。"),
      expect.stringContaining("replication_contract 批准请求 v2 已记录。"),
      expect.stringContaining("人工决定 request_evidence 已记录。"),
    ]);

    const auditSequence = screen.getByText("事件序号 5");
    expect(auditSequence).not.toBeVisible();
    await user.click(screen.getAllByText("查看安全审计信息")[0]);
    expect(auditSequence).toBeVisible();
    expect(screen.queryByText(/[a-f0-9]{64}/i)).toBeNull();
    expect(screen.queryByText(taskId)).toBeNull();
    expect(methods).toEqual(["GET"]);
    expect(window.sessionStorage.length).toBe(0);
  });
});
