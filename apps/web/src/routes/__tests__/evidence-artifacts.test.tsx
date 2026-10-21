import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import { TestApp } from "../../test/TestApp";
import { server } from "../../test/server";

const taskId = "24000000-0000-0000-0000-000000000024";

const workspace = {
  schema_version: "sv-evidence-artifacts/v1",
  authority: "postgresql",
  task: {
    task_id: taskId,
    task_revision: 3,
    subject: "换尿布反应挑战",
    performance_window: {
      start: "2026-10-01",
      end: "2026-10-08",
      timezone: "America/Los_Angeles",
    },
  },
  run: {
    run_id: "25000000-0000-0000-0000-000000000024",
    run_revision: 4,
    state: "awaiting_approval",
  },
  graph: {
    state: "available",
    public_code: "ARTIFACT_GRAPH_AVAILABLE",
    nodes: [
      {
        ref: "artifact:reference_bundle:29000000-0000-0000-0000-000000000021:v1",
        artifact_type: "reference_bundle",
        version: 1,
        status: "validated",
        evidence_level: "fact",
        proof_level: "local",
        created_at: "2026-10-21T13:00:00Z",
        is_conclusion: false,
        sources: [{ kind: "public_url" }],
        subject: {
          state: "reviewed_family_context",
          market: "US",
          locale: "en-US",
          limitations: ["只证明 family 范围，不证明具体商品一致。"],
        },
        window: {
          start: "2026-10-01",
          end: "2026-10-08",
          timezone: "America/Los_Angeles",
          basis: "artifact_observation",
        },
        limitations: ["仅用于分析，不授予素材复用权。"],
      },
      {
        ref: "artifact:replication_finding:29000000-0000-0000-0000-000000000022:v1",
        artifact_type: "replication_finding",
        version: 1,
        status: "final_with_limits",
        evidence_level: "inference",
        proof_level: "local",
        created_at: "2026-10-21T13:04:00Z",
        is_conclusion: true,
        sources: [{ kind: "human_observation" }],
        subject: {
          state: "reviewed_family_context",
          market: "US",
          locale: "en-US",
          limitations: ["未绑定 Product Snapshot。"],
        },
        window: {
          start: "2026-10-01",
          end: "2026-10-08",
          timezone: "America/Los_Angeles",
          basis: "artifact_observation",
        },
        limitations: ["不是因果结论。"],
      },
    ],
    edges: [
      {
        source_ref: "artifact:reference_bundle:29000000-0000-0000-0000-000000000021:v1",
        target_ref: "artifact:replication_finding:29000000-0000-0000-0000-000000000022:v1",
        kind: "declared_input",
        verification_state: "declared_only",
      },
    ],
    limitations: ["图谱只表示当前 Task/Run 的已验证记录。"],
  },
  evidence_planes: [
    {
      kind: "product_truth",
      state: "out_of_scope",
      public_code: "PRODUCT_TRUTH_OUT_OF_SCOPE",
      subject: null,
      window: null,
      source: "no_product_claims",
      limitations: ["若加入商品声明，必须重新绑定 Product Snapshot。"],
      proof_level: null,
    },
    {
      kind: "performance",
      state: "unavailable",
      public_code: "PERFORMANCE_EVIDENCE_UNAVAILABLE",
      subject: null,
      window: {
        start: "2026-10-01",
        end: "2026-10-08",
        timezone: "America/Los_Angeles",
        basis: "task_scope",
      },
      source: "未连接 reviewed performance package",
      limitations: ["不能把未连接数据当成零表现。"],
      proof_level: null,
    },
    {
      kind: "experiment",
      state: "quarantined",
      public_code: "EXPERIMENT_EVIDENCE_QUARANTINED",
      subject: null,
      window: null,
      source: "实验绑定需要人工复核",
      limitations: ["当前不能支持 winner 或因果结论。"],
      proof_level: "local",
    },
    {
      kind: "asset",
      state: "unavailable",
      public_code: "ASSET_EVIDENCE_UNAVAILABLE",
      subject: null,
      window: null,
      source: "未连接受控 Asset Bundle",
      limitations: ["Private Gate 不等于商业批准。"],
      proof_level: null,
    },
  ],
  comparison: {
    state: "unavailable",
    public_code: "COMPARISON_VERSION_REFS_UNAVAILABLE",
    script_ref: null,
    control_version_ref: null,
    variant_version_ref: null,
    limitations: ["缺少同一 Script 下的不可变 Control / Variant 版本引用。"],
  },
  explicit_non_effects: [
    "does_not_write_postgresql",
    "does_not_read_filesystem_or_private_assets",
    "does_not_bind_external_evidence_packages",
    "does_not_infer_control_or_variant_versions",
    "does_not_render_or_publish",
  ],
} as const;

describe("SV-Agent Evidence and Artifacts", () => {
  it("shows the canonical graph and keeps four evidence planes separate", async () => {
    const methods: string[] = [];
    server.use(
      http.get("/api/v1/sv-agent/tasks/:taskId/artifacts", ({ params, request }) => {
        expect(params.taskId).toBe(taskId);
        methods.push(request.method);
        return HttpResponse.json(workspace);
      }),
    );

    const user = userEvent.setup();
    render(<TestApp initialEntries={[`/sv-agent/tasks/${taskId}/evidence`]} />);

    expect(
      await screen.findByRole("heading", { name: "换尿布反应挑战的证据与产物" }),
    ).toBeVisible();
    expect(screen.getByText("PostgreSQL 权威投影")).toBeVisible();
    const graph = screen.getByRole("region", { name: "产物依赖图谱" });
    expect(within(graph).getByText("参考素材包 · v1")).toBeVisible();
    expect(within(graph).getByText("复刻结论 · v1")).toBeVisible();
    expect(within(graph).getByText("1 条依赖关系")).toBeVisible();

    const planes = screen.getByRole("region", { name: "四类证据" });
    expect(within(planes).getByRole("heading", { name: "Product Truth" })).toBeVisible();
    expect(within(planes).getByRole("heading", { name: "Performance" })).toBeVisible();
    expect(within(planes).getByRole("heading", { name: "Experiment" })).toBeVisible();
    expect(within(planes).getByRole("heading", { name: "Asset" })).toBeVisible();
    expect(within(planes).getByText("本任务不适用")).toBeVisible();
    expect(within(planes).getAllByText("当前不可用")).toHaveLength(2);
    expect(within(planes).getByText("暂时隔离")).toBeVisible();
    expect(screen.queryByText("0", { exact: true })).toBeNull();

    const finding = within(graph).getByText("复刻结论 · v1").closest("article");
    expect(finding).not.toBeNull();
    expect(within(finding!).getByText("人工观察")).not.toBeVisible();
    await user.click(within(finding!).getByText("查看复刻结论证据细节"));
    expect(within(finding!).getByText("人工观察")).toBeVisible();
    expect(within(finding!).getByText("只确认到 Product Family 范围")).toBeVisible();
    expect(within(finding!).getByText("2026-10-01 至 2026-10-08")).toBeVisible();
    expect(within(finding!).getByText("不是因果结论。")).toBeVisible();
    expect(within(finding!).getAllByText("本地证明")).toHaveLength(2);
    const auditRef = within(finding!).getByText(workspace.graph.nodes[1].ref);
    expect(auditRef).not.toBeVisible();
    await user.click(within(finding!).getByText("查看审计引用"));
    expect(auditRef).toBeVisible();

    const comparisonCode = screen.getByText("COMPARISON_VERSION_REFS_UNAVAILABLE");
    expect(comparisonCode).not.toBeVisible();
    await user.click(screen.getByText("查看对比审计信息"));
    expect(comparisonCode).toBeVisible();
    expect(screen.queryByRole("link", { name: "打开 Control / Variant 对比" })).toBeNull();
    expect(screen.queryByText(/winner|胜者|赢家/i)).toBeNull();
    expect(
      screen.getByText("不会读取本地文件系统或 Momcozy 私有素材库。"),
    ).toBeVisible();
    expect(
      screen.getByText("不会自动绑定外部 Performance、Experiment 或 Asset 证据包。"),
    ).toBeVisible();
    expect(
      screen.getByText("不会猜测 Control / Variant，也不会把 generic ID 当成 ScriptVersion。"),
    ).toBeVisible();
    expect(methods).toEqual(["GET"]);
    expect(window.sessionStorage.length).toBe(0);
  });

  it("shows an empty authoritative workspace when no active Run exists", async () => {
    server.use(
      http.get("/api/v1/sv-agent/tasks/:taskId/artifacts", () =>
        HttpResponse.json({
          ...workspace,
          run: null,
          graph: {
            state: "unavailable",
            public_code: "ARTIFACT_GRAPH_UNAVAILABLE",
            nodes: [],
            edges: [],
            limitations: ["尚未创建权威 Run，因此没有可展示的产物图谱。"],
          },
        }),
      ),
    );

    render(<TestApp initialEntries={[`/sv-agent/tasks/${taskId}/evidence`]} />);

    expect(
      await screen.findByText("尚未创建权威 Run，因此没有可展示的产物图谱。"),
    ).toBeVisible();
    expect(screen.getByText("尚未创建 Run")).toBeVisible();
    expect(screen.queryByText("参考素材包 · v1")).toBeNull();
  });

  it("recovers from a read failure without sending a write request", async () => {
    let attempts = 0;
    const methods: string[] = [];
    server.use(
      http.get("/api/v1/sv-agent/tasks/:taskId/artifacts", ({ request }) => {
        methods.push(request.method);
        attempts += 1;
        return attempts === 1
          ? HttpResponse.json(
              {
                type: "about:blank",
                title: "Task database unavailable",
                status: 503,
                detail: "The authoritative Task store is unavailable.",
                code: "DATABASE_UNAVAILABLE",
                request_id: "request-1",
              },
              { status: 503 },
            )
          : HttpResponse.json(workspace);
      }),
    );

    const user = userEvent.setup();
    render(<TestApp initialEntries={[`/sv-agent/tasks/${taskId}/evidence`]} />);

    const alert = await screen.findByRole("alert");
    expect(within(alert).getByText("无法读取证据与产物")).toBeVisible();
    expect(within(alert).getByText("没有 Task、Run、Artifact 或审批被修改。")).toBeVisible();
    await user.click(within(alert).getByRole("button", { name: "重新读取" }));
    expect(
      await screen.findByRole("heading", { name: "换尿布反应挑战的证据与产物" }),
    ).toBeVisible();
    expect(methods).toEqual(["GET", "GET"]);
  });
});
