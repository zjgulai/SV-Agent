import { expect, test } from "@playwright/test";

test("unsupported guarantee remains visible as a validation-failed version", async ({ page }) => {
  await page.goto("/products/new");
  await page.getByLabel("商品名称").fill("Blocked Claim E2E");
  await page.getByLabel("商品描述").fill("This guarantees results");
  await page.getByRole("button", { name: "保存商品" }).click();
  await page.getByRole("button", { name: "锁定" }).click();
  await expect(page.getByText("已锁定")).toBeVisible();
  await page.getByRole("link", { name: "生成脚本" }).click();
  await page.getByRole("button", { name: "创建生成任务" }).click();

  await expect(page.getByRole("status")).toHaveText("校验未通过", { timeout: 20_000 });
  await page.getByRole("link", { name: "查看脚本" }).click();
  await expect(page.getByRole("heading", { name: "校验未通过" })).toBeVisible();
  await expect(page.getByText("CLAIM_GUARANTEE").first()).toBeVisible();
  await expect(page.getByText("This guarantees results").first()).toBeVisible();
});
