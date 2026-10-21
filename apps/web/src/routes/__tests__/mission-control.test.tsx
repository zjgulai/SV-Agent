import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import { TestApp } from "../../test/TestApp";
import { server } from "../../test/server";

const taskId = "24000000-0000-0000-0000-000000000024";

const completeWorkspace = {
  schema_version: "sv-mission-control/v1",
  authority: "postgresql",
  task: {
    task_id: taskId,
    task_revision: 3,
    goal_track: "brand_voice_social_resonance",
    decision_question: "如何保留真实宝宝反应的传播机制，同时形成 Momcozy 自有表达？",
    subject: "换尿布反应挑战",
    platform: "tiktok",
    market: "US",
    language: "en-US",
    performance_window: {
      start: "2026-10-01",
      end: "2026-10-08",
      timezone: "America/Los_Angeles",
    },
    stop_condition: "权利或儿童安全边界不闭合时停止",
    initial_rights_state: "analysis_only",
  },
  run: {
    run_id: "25000000-0000-0000-0000-000000000024",
    task_revision: 3,
    run_revision: 4,
    state: "awaiting_approval",
    primary_mechanism: "experience-pov",
    creative_dimension: "experience_pov",
    updated_at: "2026-10-21T13:10:00Z",
  },
  stages: [
    { key: "reference_admission", label: "确认参考来源和可使用范围", status: "unknown" },
    { key: "content_decomposition", label: "拆解开头、节奏、情绪和互动结构", status: "unknown" },
    { key: "mechanism_selection", label: "只选一个主机制", status: "completed" },
    { key: "fact_and_contract", label: "绑定事实并冻结复刻合同", status: "blocked" },
    { key: "adaptation", label: "形成目标品牌适配包", status: "waiting" },
    { key: "script_and_storyboard", label: "形成脚本与 Storyboard", status: "unknown" },
    { key: "media_integrity_and_finding", label: "完成媒体完整性与复刻结论", status: "waiting" },
  ],
  current_stage: "fact_and_contract",
  plan: {
    ref: "run-plan:26000000-0000-0000-0000-000000000024:v2",
    version: 2,
    workflow_name: "viral-replication.experience-pov",
    workflow_version: "1.0.0",
    capability_catalog_version: "1.0.0",
    run_revision: 4,
    steps: [
      {
        step_id: "confirm-contract",
        order: 1,
        capability_name: "planning.viral.experience-pov",
        capability_version: "1.0.0",
        execution_mode: "planning_only",
      },
    ],
    limitations: ["No render, publish, rights, or commercial approval."],
    created_at: "2026-10-21T13:05:00Z",
  },
  blockers: [
    {
      code: "APPROVAL_REQUIRED",
      message: "Human decision required for replication_contract.",
      source_ref: "approval-request:27000000-0000-0000-0000-000000000024:v1",
    },
  ],
  next_safe_action: {
    kind: "open_approval",
    label: "Open the current decision request",
    reason: "Human approval is a separate seam and cannot be decided here.",
    reason_code: "HUMAN_APPROVAL_REQUIRED",
    interaction_intent: null,
    basis_refs: [
      "approval-request:27000000-0000-0000-0000-000000000024:v1",
    ],
    explicit_non_effects: [
      "does_not_write_postgresql",
      "does_not_decide_approval",
    ],
    execution_available: false,
  },
  tool_runs: [
    {
      ref: "tool-run:28000000-0000-0000-0000-000000000024:r3",
      tool_name: "pattern_contract.inspect",
      tool_version: "1.0.0",
      intent_summary: "检查机制与合同边界",
      effect_class: "read",
      status: "completed",
      stable_error_code: null,
      recovery_action: null,
      started_at: "2026-10-21T13:00:00Z",
      finished_at: "2026-10-21T13:01:00Z",
      updated_at: "2026-10-21T13:01:00Z",
    },
  ],
  tool_runs_truncated: false,
  current_artifact: {
    ref: "artifact:replication_contract:29000000-0000-0000-0000-000000000024:v1",
    artifact_type: "replication_contract",
    version: 1,
    status: "awaiting_approval",
    evidence_level: "fact",
    proof_level: "local",
    created_at: "2026-10-21T13:04:00Z",
  },
  explanation: {
    summary: "当前复刻合同已形成，但仍需独立人工决定后才能继续。",
    citations: [
      {
        kind: "artifact",
        ref: "artifact:replication_contract:29000000-0000-0000-0000-000000000024:v1",
      },
    ],
  },
} as const;

describe("SV-Agent Mission Control", () => {
  it("shows the authoritative seven-stage workspace and cited current state", async () => {
    server.use(
      http.get("/api/v1/sv-agent/tasks/:taskId", ({ params }) => {
        expect(params.taskId).toBe(taskId);
        return HttpResponse.json(completeWorkspace);
      }),
    );

    const user = userEvent.setup();
    render(<TestApp initialEntries={[`/sv-agent/tasks/${taskId}`]} />);

    expect(
      await screen.findByRole("heading", { name: "换尿布反应挑战" }),
    ).toBeVisible();
    expect(screen.getByText("PostgreSQL 权威状态")).toBeVisible();
    const path = screen.getByRole("region", { name: "七步复刻路径" });
    expect(within(path).getAllByRole("listitem")).toHaveLength(7);
    expect(within(path).getByText("已证实完成 1 · 未知 3")).toBeVisible();
    expect(within(path).getByText("绑定事实并冻结复刻合同")).toBeVisible();
    expect(screen.getByRole("heading", { name: "当前 RunPlan" })).toBeVisible();
    expect(screen.getByText("planning.viral.experience-pov")).toBeVisible();
    expect(screen.getByRole("heading", { name: "当前产物" })).toBeVisible();
    expect(screen.getByText("replication_contract · v1")).toBeVisible();
    expect(screen.getByRole("link", { name: "查看证据与产物" })).toHaveAttribute(
      "href",
      `/sv-agent/tasks/${taskId}/evidence`,
    );
    expect(screen.getByText("绑定事实并冻结复刻合同 · 已阻断")).toBeVisible();
    expect(
      screen.getByText("当前 Run 等待独立人工决定；Mission Control 不会代为决定。"),
    ).toBeVisible();
    expect(
      screen.queryByText("Human decision required for replication_contract."),
    ).toBeNull();
    expect(screen.getByText("查看待处理决定")).toBeVisible();
    expect(screen.getByText("检查机制与合同边界")).toBeVisible();
    expect(
      screen.getByText("当前复刻合同已形成，但仍需独立人工决定后才能继续。"),
    ).toBeVisible();
    const citation = within(screen.getByLabelText("解释引用")).getByText(
      "artifact:replication_contract:29000000-0000-0000-0000-000000000024:v1",
    );
    expect(citation).not.toBeVisible();
    await user.click(screen.getByText("查看引用审计信息"));
    expect(citation).toBeVisible();

    const artifactRef = screen.getByText(
      "artifact:replication_contract:29000000-0000-0000-0000-000000000024:v1",
      { selector: ".mission-artifact code" },
    );
    expect(artifactRef).not.toBeVisible();
    await user.click(screen.getByText("查看产物审计信息"));
    expect(artifactRef).toBeVisible();

    const blockerArticle = screen
      .getByText("当前 Run 等待独立人工决定；Mission Control 不会代为决定。")
      .closest("article");
    expect(blockerArticle).not.toBeNull();
    const blockerRef = within(blockerArticle!).getByText(
      "approval-request:27000000-0000-0000-0000-000000000024:v1",
    );
    expect(blockerRef).not.toBeVisible();
    await user.click(screen.getByText("查看阻塞来源"));
    expect(blockerRef).toBeVisible();
  });

  it("previews a closed AgentCommand without sending or storing it", async () => {
    const methods: string[] = [];
    server.use(
      http.get("/api/v1/sv-agent/tasks/:taskId", ({ request }) => {
        methods.push(request.method);
        return HttpResponse.json(completeWorkspace);
      }),
    );
    const user = userEvent.setup();
    render(<TestApp initialEntries={[`/sv-agent/tasks/${taskId}`]} />);

    await screen.findByRole("heading", { name: "换尿布反应挑战" });
    await user.selectOptions(screen.getByLabelText("命令意图"), "request_evidence");
    await user.type(
      screen.getByLabelText("给 SV-Agent 的说明"),
      "请先补齐参考使用范围证据",
    );
    await user.click(screen.getByRole("button", { name: "预览 AgentCommand" }));

    const preview = screen.getByRole("region", { name: "AgentCommand 预览" });
    expect(within(preview).getByText("request_evidence")).toBeVisible();
    expect(within(preview).getByText("Task revision 3")).toBeVisible();
    expect(within(preview).getByText("只会形成命令预览，不会提交或执行。"))
      .toBeVisible();
    expect(
      within(preview).getByText(
        "这不是 HumanApproval 的 request_evidence 决定，也不会关闭 ApprovalRequest。",
      ),
    ).toBeVisible();
    expect(within(preview).getByText("请先补齐参考使用范围证据")).toBeVisible();
    expect(screen.queryByRole("option", { name: /approve|reject|批准|拒绝/i })).toBeNull();

    await user.selectOptions(screen.getByLabelText("命令意图"), "stop");
    await user.click(screen.getByRole("button", { name: "预览 AgentCommand" }));
    expect(
      within(preview).getByText(
        "这不是 HumanApproval 的 stop 决定，也不会关闭 ApprovalRequest。",
      ),
    ).toBeVisible();

    expect(screen.getByRole("option", { name: "恢复原命令" })).toBeDisabled();
    expect(
      screen.getByText(
        "当前投影没有可恢复的 command receipt；resume_recovery 不可用。",
      ),
    ).toBeVisible();
    expect(methods).toEqual(["GET"]);
    expect(window.sessionStorage.length).toBe(0);
  });

  it("keeps an ambiguous Plan and Artifact frontier unknown instead of selecting a latest row", async () => {
    server.use(
      http.get("/api/v1/sv-agent/tasks/:taskId", () =>
        HttpResponse.json({
          ...completeWorkspace,
          stages: completeWorkspace.stages.map((stage) => ({
            ...stage,
            status: "unknown",
          })),
          current_stage: "mechanism_selection",
          plan: null,
          current_artifact: null,
          tool_runs: [],
          tool_runs_truncated: false,
          blockers: [
            {
              code: "PLAN_FRONTIER_AMBIGUOUS",
              message: "没有唯一、精确绑定当前 Run revision 的 RunPlan。",
              source_ref: "run:25000000-0000-0000-0000-000000000024:r4",
            },
            {
              code: "ARTIFACT_FRONTIER_AMBIGUOUS",
              message: "没有唯一、精确绑定当前 Run revision 的 Artifact。",
              source_ref: "run:25000000-0000-0000-0000-000000000024:r4",
            },
          ],
          explanation: {
            summary: "当前前沿不唯一，因此不选择任意最新记录。",
            citations: [],
          },
        }),
      ),
    );

    render(<TestApp initialEntries={[`/sv-agent/tasks/${taskId}`]} />);

    await screen.findByRole("heading", { name: "换尿布反应挑战" });
    expect(screen.getByText("RunPlan 前沿不唯一，界面不会选择任意最新记录。"))
      .toBeVisible();
    expect(screen.getByText("Artifact 前沿不唯一，界面不会选择任意最新记录。"))
      .toBeVisible();
    expect(screen.getAllByText("尚无权威证明")).toHaveLength(7);
    expect(screen.getByText("只选一个主机制 · 尚无权威证明")).toBeVisible();
    expect(screen.getByText("PLAN_FRONTIER_AMBIGUOUS")).toBeVisible();
    expect(screen.getByText("ARTIFACT_FRONTIER_AMBIGUOUS")).toBeVisible();
    expect(screen.getByText("暂无 Artifact 或 Evidence 引用，因此不生成额外结论。"))
      .toBeVisible();
  });

  it("renders a saved Task without inventing a Run, Plan, or Artifact", async () => {
    server.use(
      http.get("/api/v1/sv-agent/tasks/:taskId", () =>
        HttpResponse.json({
          ...completeWorkspace,
          run: null,
          stages: completeWorkspace.stages.map((stage, index) => ({
            ...stage,
            status: index === 0 ? "active" : "waiting",
          })),
          current_stage: "reference_admission",
          plan: null,
          blockers: [
            {
              code: "RUN_NOT_STARTED",
              message: "Task 已保存，但还没有权威 Run。",
              source_ref: `task:${taskId}:r3`,
            },
          ],
          next_safe_action: {
            kind: "preview_request_plan",
            label: "Preview a plan request",
            reason: "Mission Control is read-only and no public Run writer is available.",
            reason_code: "PLAN_REQUEST_PREVIEW_ONLY",
            interaction_intent: "request_plan",
            basis_refs: [`task:${taskId}:r3`],
            explicit_non_effects: [
              "does_not_write_postgresql",
              "does_not_dispatch_tool",
            ],
            execution_available: false,
          },
          tool_runs: [],
          tool_runs_truncated: false,
          current_artifact: null,
          explanation: {
            summary: "The Task is saved, but no authoritative Run exists yet.",
            citations: [{ kind: "task", ref: `task:${taskId}:r3` }],
          },
        }),
      ),
    );

    render(<TestApp initialEntries={[`/sv-agent/tasks/${taskId}`]} />);

    await screen.findByRole("heading", { name: "换尿布反应挑战" });
    expect(screen.getByText("尚未创建 Run")).toBeVisible();
    expect(screen.getAllByText("Task 已保存，但还没有权威 Run。")[0]).toBeVisible();
    expect(
      screen.queryByText("The Task is saved, but no authoritative Run exists yet."),
    ).toBeNull();
    expect(screen.getByText("当前没有已持久化 RunPlan；界面不会根据对话猜测计划。"))
      .toBeVisible();
    expect(screen.getByText("尚未开始 Run，因此没有当前 Artifact。"))
      .toBeVisible();
    expect(screen.getByText("已证实完成 0 · 未知 0")).toBeVisible();
  });

  it.each([
    {
      code: "ARTIFACT_FRONTIER_UNVERIFIED",
      message: "候选 Artifact 缺少 runtime lineage。",
      expected:
        "发现候选 Artifact，但没有权威 lineage 验证；当前产物保持未知。",
    },
    {
      code: "ARTIFACT_FRONTIER_UNAVAILABLE",
      message: "当前 Run revision 没有 Artifact。",
      expected:
        "当前 Run revision 没有唯一且有效的 Artifact；当前产物保持未知。",
    },
  ])("explains the $code Artifact frontier without guessing", async ({ code, message, expected }) => {
    server.use(
      http.get("/api/v1/sv-agent/tasks/:taskId", () =>
        HttpResponse.json({
          ...completeWorkspace,
          current_artifact: null,
          blockers: [{ code, message, source_ref: `run:${completeWorkspace.run.run_id}:r4` }],
        }),
      ),
    );

    render(<TestApp initialEntries={[`/sv-agent/tasks/${taskId}`]} />);

    await screen.findByRole("heading", { name: "换尿布反应挑战" });
    expect(screen.getByText(expected)).toBeVisible();
  });

  it("discloses when ToolRuns are truncated", async () => {
    server.use(
      http.get("/api/v1/sv-agent/tasks/:taskId", () =>
        HttpResponse.json({ ...completeWorkspace, tool_runs_truncated: true }),
      ),
    );

    render(<TestApp initialEntries={[`/sv-agent/tasks/${taskId}`]} />);

    await screen.findByRole("heading", { name: "换尿布反应挑战" });
    expect(
      screen.getByText("这里只显示最近 20 条 ToolRun；更早记录未在本页展开。"),
    ).toBeVisible();
  });

  it("shows a read error and retries the same GET without mutating state", async () => {
    let requests = 0;
    const methods: string[] = [];
    server.use(
      http.get("/api/v1/sv-agent/tasks/:taskId", ({ request }) => {
        requests += 1;
        methods.push(request.method);
        if (requests === 1) {
          return HttpResponse.json(
            {
              type: "about:blank",
              title: "Task database unavailable",
              status: 503,
              detail: "The authoritative Task store is unavailable.",
              code: "DATABASE_UNAVAILABLE",
              request_id: "safe-request-id",
            },
            { status: 503 },
          );
        }
        return HttpResponse.json(completeWorkspace);
      }),
    );
    const user = userEvent.setup();

    render(<TestApp initialEntries={[`/sv-agent/tasks/${taskId}`]} />);

    const alert = await screen.findByRole("alert");
    expect(within(alert).getByText("权威状态读取失败。没有 Task、Run 或审批被修改。"))
      .toBeVisible();
    await user.click(within(alert).getByRole("button", { name: "重新读取" }));

    expect(await screen.findByRole("heading", { name: "换尿布反应挑战" }))
      .toBeVisible();
    expect(methods).toEqual(["GET", "GET"]);
  });

  it("keeps an unknown Tool error safe and Chinese while retaining its stable code", async () => {
    server.use(
      http.get("/api/v1/sv-agent/tasks/:taskId", () =>
        HttpResponse.json({
          ...completeWorkspace,
          blockers: [
            {
              code: "PROVIDER_TIMEOUT",
              message: "Provider returned an internal transport detail.",
              source_ref: "tool-run:28000000-0000-0000-0000-000000000024:r3",
            },
          ],
        }),
      ),
    );

    render(<TestApp initialEntries={[`/sv-agent/tasks/${taskId}`]} />);

    await screen.findByRole("heading", { name: "换尿布反应挑战" });
    expect(screen.getByText("PROVIDER_TIMEOUT")).toBeVisible();
    expect(
      screen.getByText(
        "记录到一项技术执行问题；请按稳定错误码检查，本页不会自动重试。",
      ),
    ).toBeVisible();
    expect(
      screen.queryByText("Provider returned an internal transport detail."),
    ).toBeNull();
  });
});
