import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, it, vi } from "vitest";

import { TestApp } from "../../test/TestApp";
import { server } from "../../test/server";


const emptyInbox = {
  schema_version: "sv-task-inbox/v1",
  authority: "postgresql",
  ordering_policy_version: "sv-task-inbox-order/v1",
  items: [],
  truncated: false,
};


describe("SV-Agent New Task brief", () => {
  it("saves a Brand Voice brief locally without a Product Snapshot or server mutation", async () => {
    const methods: string[] = [];
    server.use(
      http.all("/api/v1/sv-agent/*", ({ request }) => {
        methods.push(request.method);
        if (request.method === "GET") return HttpResponse.json(emptyInbox);
        return HttpResponse.json({ detail: "unexpected mutation" }, { status: 500 });
      }),
    );
    const user = userEvent.setup();
    render(<TestApp initialEntries={["/sv-agent/tasks/new"]} />);

    expect(
      screen.getByRole("heading", { name: "新建复刻任务草稿" }),
    ).toBeVisible();
    await user.click(
      screen.getByRole("radio", { name: /^品牌声量 \/ Social Resonance/ }),
    );
    await user.type(screen.getByLabelText("主题"), "Momcozy 换尿布时的宝宝反应");
    await user.type(
      screen.getByLabelText("决策问题"),
      "如何保留真实宝宝反应的分享机制，同时形成 Momcozy 自有表达？",
    );
    await user.type(
      screen.getByLabelText("公开参考链接"),
      "https://www.tiktok.com/@reference/video/123",
    );
    await user.type(screen.getByLabelText("观察开始日期"), "2026-10-01");
    await user.type(screen.getByLabelText("观察结束日期"), "2026-10-08");
    await user.selectOptions(screen.getByLabelText("权利初始状态"), "unknown");
    await user.selectOptions(
      screen.getByLabelText("儿童安全初始状态"),
      "review_required",
    );
    await user.click(
      screen.getByRole("checkbox", { name: /权利仍需单独人工确认/ }),
    );
    await user.click(
      screen.getByRole("checkbox", { name: /儿童安全仍需单独人工确认/ }),
    );

    expect(screen.queryByLabelText("Product Snapshot ID")).toBeNull();
    await user.click(screen.getByRole("button", { name: "保存到本浏览器" }));

    expect(
      await screen.findByRole("heading", { name: "Task 与决定收件箱" }),
    ).toBeVisible();
    const drafts = screen.getByRole("region", { name: "浏览器本地草稿" });
    expect(within(drafts).getByText("非权威 · 本机")).toBeVisible();
    expect(
      within(drafts).getByText("Momcozy 换尿布时的宝宝反应"),
    ).toBeVisible();
    expect(within(drafts).getByText("尚未写入 PostgreSQL")).toBeVisible();
    expect(methods).toEqual(["GET"]);
  });

  it("requires a Product Snapshot candidate when Brand Voice introduces product claims", async () => {
    const user = userEvent.setup();
    render(<TestApp initialEntries={["/sv-agent/tasks/new"]} />);

    expect(screen.queryByLabelText("Product Snapshot ID")).toBeNull();
    await user.click(screen.getByRole("radio", { name: "包含产品声明" }));
    expect(screen.getByLabelText("Product Snapshot ID")).toBeRequired();
    await user.click(screen.getByRole("radio", { name: "不包含产品声明" }));
    expect(screen.queryByLabelText("Product Snapshot ID")).toBeNull();
  });

  it("restores every Product Replication field when a saved draft is reopened", async () => {
    server.use(
      http.get("/api/v1/sv-agent/tasks", () => HttpResponse.json(emptyInbox)),
    );
    const user = userEvent.setup();
    render(<TestApp initialEntries={["/sv-agent/tasks/new"]} />);

    await user.click(screen.getByRole("radio", { name: /^产品复刻/ }));
    await user.type(screen.getByLabelText("主题"), "M5 Smart 爆款复刻");
    await user.type(
      screen.getByLabelText("决策问题"),
      "哪一种真实演示机制最适合进入下一轮创意评审？",
    );
    await user.type(
      screen.getByLabelText("公开参考链接"),
      "https://www.instagram.com/reel/reference",
    );
    await user.type(screen.getByLabelText("Product Snapshot ID"), "snapshot-m5-v3");
    await user.selectOptions(screen.getByLabelText("平台"), "instagram");
    await user.clear(screen.getByLabelText("市场代码"));
    await user.type(screen.getByLabelText("市场代码"), "DE");
    await user.clear(screen.getByLabelText("语言"));
    await user.type(screen.getByLabelText("语言"), "de-DE");
    await user.type(screen.getByLabelText("观察开始日期"), "2026-10-02");
    await user.type(screen.getByLabelText("观察结束日期"), "2026-10-12");
    await user.clear(screen.getByLabelText("时区"));
    await user.type(screen.getByLabelText("时区"), "Europe/Berlin");
    await user.clear(screen.getByLabelText("停止条件"));
    await user.type(
      screen.getByLabelText("停止条件"),
      "Product Snapshot 失效或事实门不通过时停止",
    );
    await user.selectOptions(screen.getByLabelText("权利初始状态"), "analysis_only");
    await user.selectOptions(
      screen.getByLabelText("儿童安全初始状态"),
      "not_applicable_user_asserted",
    );
    await user.click(
      screen.getByRole("checkbox", { name: /权利仍需单独人工确认/ }),
    );
    await user.click(
      screen.getByRole("checkbox", { name: /儿童安全仍需单独人工确认/ }),
    );

    await user.click(screen.getByRole("button", { name: "保存到本浏览器" }));
    const firstEditLink = await screen.findByRole("link", { name: "继续编辑" });
    const firstEditHref = firstEditLink.getAttribute("href");
    await user.click(firstEditLink);

    expect(screen.getByRole("radio", { name: /^产品复刻/ })).toBeChecked();
    expect(screen.getByLabelText("主题")).toHaveValue("M5 Smart 爆款复刻");
    expect(screen.getByLabelText("决策问题")).toHaveValue(
      "哪一种真实演示机制最适合进入下一轮创意评审？",
    );
    expect(screen.getByLabelText("公开参考链接")).toHaveValue(
      "https://www.instagram.com/reel/reference",
    );
    expect(screen.getByLabelText("Product Snapshot ID")).toHaveValue(
      "snapshot-m5-v3",
    );
    expect(screen.getByLabelText("平台")).toHaveValue("instagram");
    expect(screen.getByLabelText("市场代码")).toHaveValue("DE");
    expect(screen.getByLabelText("语言")).toHaveValue("de-DE");
    expect(screen.getByLabelText("观察开始日期")).toHaveValue("2026-10-02");
    expect(screen.getByLabelText("观察结束日期")).toHaveValue("2026-10-12");
    expect(screen.getByLabelText("时区")).toHaveValue("Europe/Berlin");
    expect(screen.getByLabelText("停止条件")).toHaveValue(
      "Product Snapshot 失效或事实门不通过时停止",
    );
    expect(screen.getByLabelText("权利初始状态")).toHaveValue("analysis_only");
    expect(screen.getByLabelText("儿童安全初始状态")).toHaveValue(
      "not_applicable_user_asserted",
    );
    expect(
      screen.getByRole("checkbox", { name: /权利仍需单独人工确认/ }),
    ).toBeChecked();
    expect(
      screen.getByRole("checkbox", { name: /儿童安全仍需单独人工确认/ }),
    ).toBeChecked();

    await user.clear(screen.getByLabelText("主题"));
    await user.type(screen.getByLabelText("主题"), "M5 Smart 爆款复刻 · 更新");
    await user.click(screen.getByRole("button", { name: "保存到本浏览器" }));

    const drafts = await screen.findByRole("region", { name: "浏览器本地草稿" });
    expect(within(drafts).queryByText("M5 Smart 爆款复刻")).toBeNull();
    expect(within(drafts).getByText("M5 Smart 爆款复刻 · 更新")).toBeVisible();
    expect(within(drafts).getAllByText("尚未写入 PostgreSQL")).toHaveLength(1);
    expect(within(drafts).getByRole("link", { name: "继续编辑" })).toHaveAttribute(
      "href",
      firstEditHref,
    );
  });

  it("focuses the first custom-invalid field and explains how to recover", async () => {
    const user = userEvent.setup();
    render(<TestApp initialEntries={["/sv-agent/tasks/new"]} />);

    await user.type(screen.getByLabelText("主题"), "   ");
    await user.type(screen.getByLabelText("决策问题"), "哪种反应机制值得继续研究？");
    await user.type(
      screen.getByLabelText("公开参考链接"),
      "https://www.tiktok.com/@reference/video/789",
    );
    await user.type(screen.getByLabelText("观察开始日期"), "2026-10-05");
    await user.type(screen.getByLabelText("观察结束日期"), "2026-10-10");
    await user.click(
      screen.getByRole("checkbox", { name: /权利仍需单独人工确认/ }),
    );
    await user.click(
      screen.getByRole("checkbox", { name: /儿童安全仍需单独人工确认/ }),
    );
    await user.click(screen.getByRole("button", { name: "保存到本浏览器" }));

    expect(screen.getByRole("alert")).toHaveTextContent("请检查公开链接");
    expect(screen.getByLabelText("主题")).toHaveAttribute("aria-invalid", "true");
    await waitFor(() => expect(screen.getByLabelText("主题")).toHaveFocus());
  });

  it("keeps the completed brief visible when browser storage rejects the write", async () => {
    const storageAccess = vi
      .spyOn(window, "sessionStorage", "get")
      .mockImplementation(() => {
        throw new DOMException("Storage unavailable", "QuotaExceededError");
      });
    try {
      const user = userEvent.setup();
      render(<TestApp initialEntries={["/sv-agent/tasks/new"]} />);

      await user.type(screen.getByLabelText("主题"), "宝宝反应声量任务");
      await user.type(screen.getByLabelText("决策问题"), "哪种反应机制值得继续研究？");
      await user.type(
        screen.getByLabelText("公开参考链接"),
        "https://www.tiktok.com/@reference/video/456",
      );
      await user.type(screen.getByLabelText("观察开始日期"), "2026-10-05");
      await user.type(screen.getByLabelText("观察结束日期"), "2026-10-10");
      await user.click(
        screen.getByRole("checkbox", { name: /权利仍需单独人工确认/ }),
      );
      await user.click(
        screen.getByRole("checkbox", { name: /儿童安全仍需单独人工确认/ }),
      );

      await user.click(screen.getByRole("button", { name: "保存到本浏览器" }));

      expect(screen.getByRole("alert")).toHaveTextContent(
        "浏览器阻止本地存储，草稿未保存",
      );
      expect(screen.getByRole("heading", { name: "新建复刻任务草稿" })).toBeVisible();
      expect(screen.getByLabelText("主题")).toHaveValue("宝宝反应声量任务");
      expect(
        screen.queryByRole("heading", { name: "Task 与决定收件箱" }),
      ).toBeNull();
    } finally {
      storageAccess.mockRestore();
    }
  });

  it.each([
    ["malformed JSON", "{not-json"],
    [
      "oversized envelope",
      JSON.stringify({
        schema_version: "sv-new-task-drafts/v2",
        drafts: [],
        padding: "界".repeat(90_000),
      }),
    ],
  ])("replaces a corrupted local envelope (%s) without hiding persisted Tasks", async (_case, storedEnvelope) => {
    window.sessionStorage.setItem("sv-agent-new-task-drafts/v2", storedEnvelope);
    server.use(
      http.get("/api/v1/sv-agent/tasks", () =>
        HttpResponse.json({
          ...emptyInbox,
          items: [
            {
              task_id: "24000000-0000-0000-0000-000000000021",
              task_revision: 1,
              goal_track: "brand_voice_social_resonance",
              subject: "PostgreSQL 中的 Task",
              decision_question: "服务器 Task 是否仍然可见？",
              active_run_id: null,
              active_run_revision: null,
              run_state: null,
              pending_decision_count: 0,
              pending_gate_kinds: [],
              lane: "not_started",
              ordering_reason: "run_not_started",
              priority_at: "2026-10-21T12:00:00Z",
            },
          ],
        }),
      ),
    );
    const user = userEvent.setup();
    render(<TestApp initialEntries={["/sv-agent/tasks/new"]} />);

    await user.type(screen.getByLabelText("主题"), "替换损坏草稿");
    await user.type(screen.getByLabelText("决策问题"), "能否恢复安全的本地草稿？");
    await user.type(
      screen.getByLabelText("公开参考链接"),
      "https://www.youtube.com/shorts/reference",
    );
    await user.type(screen.getByLabelText("观察开始日期"), "2026-10-06");
    await user.type(screen.getByLabelText("观察结束日期"), "2026-10-11");
    await user.click(
      screen.getByRole("checkbox", { name: /权利仍需单独人工确认/ }),
    );
    await user.click(
      screen.getByRole("checkbox", { name: /儿童安全仍需单独人工确认/ }),
    );
    await user.click(screen.getByRole("button", { name: "保存到本浏览器" }));

    const persisted = await screen.findByRole("region", { name: "已保存的 Task" });
    const drafts = screen.getByRole("region", { name: "浏览器本地草稿" });
    expect(within(persisted).getByText("PostgreSQL 中的 Task")).toBeVisible();
    expect(within(drafts).getByText("替换损坏草稿")).toBeVisible();
    expect(within(drafts).getByText("尚未写入 PostgreSQL")).toBeVisible();
  });
});
