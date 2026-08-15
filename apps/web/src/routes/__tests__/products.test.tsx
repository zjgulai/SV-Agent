import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import { TestApp } from "../../test/TestApp";
import { server } from "../../test/server";

describe("product facts workspace", () => {
  it("creates a manual product and shows proposed facts", async () => {
    const user = userEvent.setup();
    render(<TestApp initialEntries={["/products/new"]} />);

    await user.type(screen.getByLabelText("商品名称"), "Pulse Mix");
    await user.type(screen.getByLabelText("商品描述"), "Resealable drink mix pouch");
    await user.click(screen.getByRole("button", { name: "保存商品" }));

    expect(await screen.findByRole("heading", { name: "Pulse Mix" })).toBeVisible();
    expect(screen.getByText("待确认事实")).toBeVisible();
  });

  it("restores a product detail directly from the API", async () => {
    render(<TestApp initialEntries={["/products/product-1"]} />);

    expect(await screen.findByRole("heading", { name: "Pulse Mix" })).toBeVisible();
    expect(screen.getAllByText("Resealable drink mix pouch")).toHaveLength(3);
  });

  it("shows a locked fact conflict beside the fact", async () => {
    server.use(
      http.patch("/api/v1/products/:productId/facts/:factId", () =>
        HttpResponse.json(
          {
            type: "about:blank",
            title: "Fact state conflict",
            status: 409,
            detail: "Locked facts cannot be changed in place.",
            code: "FACT_STATE_CONFLICT",
            request_id: "request-1",
          },
          { status: 409 },
        ),
      ),
    );
    const user = userEvent.setup();
    render(<TestApp initialEntries={["/products/product-1"]} />);

    await user.click(await screen.findByRole("button", { name: "锁定" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Locked facts cannot be changed in place.",
    );
  });

  it("queues a public URL import without rendering remote HTML", async () => {
    server.use(
      http.get("/api/v1/jobs/import-job-1", () =>
        HttpResponse.json({
          id: "import-job-1",
          job_type: "product_import",
          state: "queued",
          attempt_count: 0,
          error_code: null,
          error_detail: null,
          result_id: "source-1",
        }),
      ),
    );
    const user = userEvent.setup();
    render(<TestApp initialEntries={["/products/new"]} />);

    await user.click(screen.getByRole("button", { name: "公开 URL 导入" }));
    await user.type(screen.getByLabelText(/^公开商品 URL/), "https://example.com/product");
    await user.click(screen.getByRole("button", { name: "开始安全导入" }));

    expect(await screen.findByRole("status")).toHaveTextContent("等待安全导入");
  });

  it("uses a fresh idempotency key after a successful URL import", async () => {
    const keys: string[] = [];
    server.use(
      http.post("/api/v1/product-imports", ({ request }) => {
        keys.push(request.headers.get("idempotency-key") ?? "");
        return HttpResponse.json(
          { id: `import-job-${keys.length}`, state: "queued", source_id: "source-1" },
          { status: 202 },
        );
      }),
      http.get("/api/v1/jobs/:id", () =>
        HttpResponse.json({
          id: "import-job",
          job_type: "product_import",
          state: "queued",
          attempt_count: 0,
          error_code: null,
          error_detail: null,
          result_id: "source-1",
        }),
      ),
    );
    const user = userEvent.setup();
    const first = render(<TestApp initialEntries={["/products/new"]} />);
    await user.click(screen.getByRole("button", { name: "公开 URL 导入" }));
    await user.type(screen.getByLabelText(/^公开商品 URL/), "https://example.com/product");
    await user.click(screen.getByRole("button", { name: "开始安全导入" }));
    await screen.findByRole("status");
    first.unmount();

    render(<TestApp initialEntries={["/products/new"]} />);
    await user.click(screen.getByRole("button", { name: "公开 URL 导入" }));
    await user.type(screen.getByLabelText(/^公开商品 URL/), "https://example.com/product");
    await user.click(screen.getByRole("button", { name: "开始安全导入" }));
    await screen.findByRole("status");

    expect(keys).toHaveLength(2);
    expect(keys[0]).not.toBe(keys[1]);
    expect(keys.every((key) => /^[0-9a-f-]{36}$/i.test(key))).toBe(true);
  });

  it("opens the accepted job when a URL import returns HTML with Location", async () => {
    const submits: string[] = [];
    server.use(
      http.post("/api/v1/product-imports", ({ request }) => {
        submits.push(request.headers.get("idempotency-key") ?? "");
        return new HttpResponse("<html>accepted</html>", {
          status: 202,
          headers: { Location: "/api/v1/jobs/import-known" },
        });
      }),
      http.get("/api/v1/jobs/import-known", () =>
        HttpResponse.json({
          id: "import-known",
          job_type: "product_import",
          state: "queued",
          attempt_count: 0,
          error_code: null,
          error_detail: null,
          result_id: "source-1",
        }),
      ),
    );
    const user = userEvent.setup();
    render(<TestApp initialEntries={["/products/new"]} />);

    await user.click(screen.getByRole("button", { name: "公开 URL 导入" }));
    await user.type(screen.getByLabelText(/^公开商品 URL/), "https://example.com/product");
    await user.click(screen.getByRole("button", { name: "开始安全导入" }));

    expect(await screen.findByRole("status")).toHaveTextContent("等待安全导入");
    expect(submits).toHaveLength(1);
  });

  it("replays an unknown URL import with the exact same request after refresh", async () => {
    const requests: Array<{ key: string; body: unknown }> = [];
    server.use(
      http.post("/api/v1/product-imports", async ({ request }) => {
        requests.push({
          key: request.headers.get("idempotency-key") ?? "",
          body: await request.json(),
        });
        if (requests.length === 1) return HttpResponse.error();
        return HttpResponse.json(
          { id: "import-recovered", state: "queued", source_id: "source-1" },
          { status: 202 },
        );
      }),
      http.get("/api/v1/jobs/import-recovered", () =>
        HttpResponse.json({
          id: "import-recovered",
          job_type: "product_import",
          state: "queued",
          attempt_count: 0,
          error_code: null,
          error_detail: null,
          result_id: "source-1",
        }),
      ),
    );
    const user = userEvent.setup();
    const first = render(<TestApp initialEntries={["/products/new"]} />);
    await user.click(screen.getByRole("button", { name: "公开 URL 导入" }));
    await user.type(screen.getByLabelText(/^公开商品 URL/), "https://example.com/product");
    await user.click(screen.getByRole("button", { name: "开始安全导入" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("请求状态未知");
    first.unmount();

    render(<TestApp initialEntries={["/products/new"]} />);
    await user.click(screen.getByRole("button", { name: "公开 URL 导入" }));
    await user.click(await screen.findByRole("button", { name: "恢复原请求" }));

    expect(await screen.findByRole("status")).toHaveTextContent("等待安全导入");
    expect(requests).toHaveLength(2);
    expect(requests[1]).toEqual(requests[0]);
  });
});
