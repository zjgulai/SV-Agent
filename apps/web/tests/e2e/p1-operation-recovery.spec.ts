import { expect, test, type Page } from "@playwright/test";

async function openReadyGeneration(page: Page, title: string) {
  await page.goto("/products/new");
  await page.getByLabel("商品名称").fill(title);
  await page.getByLabel("商品描述").fill("The pouch is resealable");
  await page.getByRole("button", { name: "保存商品" }).click();
  await page.getByRole("button", { name: "确认" }).click();
  await page.getByRole("button", { name: "锁定" }).click();
  await page.getByRole("link", { name: "生成脚本" }).click();
  await page.getByRole("button", { name: "纳入" }).click();
}

test("opens the durable Job when a successful generation response is malformed", async ({ page }) => {
  let createdJobId = "";
  let postCount = 0;
  await page.route("**/api/v1/products/*/script-generations", async (route) => {
    postCount += 1;
    const response = await route.fetch();
    const job = await response.json() as { id: string };
    createdJobId = job.id;
    await route.fulfill({
      status: 202,
      headers: {
        "Content-Type": "text/html; charset=utf-8",
        Location: `/api/v1/jobs/${job.id}`,
      },
      body: "<html><body>upstream proxy body</body></html>",
    });
  });

  await openReadyGeneration(page, "Malformed Response Recovery E2E");
  await page.getByRole("button", { name: "创建生成任务" }).click();

  await expect.poll(() => createdJobId).not.toBe("");
  await expect(page).toHaveURL(new RegExp(`/jobs/${createdJobId}$`));
  expect(postCount).toBe(1);
});

test("replays the exact original request after a transport failure", async ({ page }) => {
  const requestBodies: string[] = [];
  const idempotencyKeys: string[] = [];
  let createdJobId = "";
  await page.route("**/api/v1/products/*/script-generations", async (route) => {
    requestBodies.push(route.request().postData() ?? "");
    idempotencyKeys.push(route.request().headers()["idempotency-key"] ?? "");
    if (requestBodies.length === 1) {
      const response = await route.fetch();
      createdJobId = (await response.json() as { id: string }).id;
      await route.abort("connectionfailed");
      return;
    }
    await route.continue();
  });

  await openReadyGeneration(page, "Transport Recovery E2E");
  await page.getByRole("button", { name: "创建生成任务" }).click();
  await expect(page.getByRole("status")).toContainText("请求状态未知");

  await page.reload();
  await expect(page.getByRole("status")).toContainText("请求状态未知");
  await page.getByRole("button", { name: "恢复原请求" }).click();

  await expect.poll(() => createdJobId).not.toBe("");
  await expect(page).toHaveURL(new RegExp(`/jobs/${createdJobId}$`));
  expect(requestBodies).toHaveLength(2);
  expect(requestBodies[1]).toBe(requestBodies[0]);
  expect(idempotencyKeys[1]).toBe(idempotencyKeys[0]);
});
