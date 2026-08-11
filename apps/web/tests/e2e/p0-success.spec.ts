import { expect, test } from "@playwright/test";

test("manual facts produce, version, compare, and export an acceptable script", async ({ page }) => {
  await page.goto("/products/new");
  await page.getByLabel("商品名称").fill("Pulse Mix E2E");
  await page.getByLabel("商品描述").fill("The pouch is resealable");
  await page.getByRole("button", { name: "保存商品" }).click();

  await expect(page.getByRole("heading", { name: "Pulse Mix E2E" })).toBeVisible();
  await page.getByRole("button", { name: "确认" }).click();
  await expect(page.getByText("已确认")).toBeVisible();
  await page.getByRole("button", { name: "锁定" }).click();
  await expect(page.getByText("已锁定")).toBeVisible();

  await page.getByRole("link", { name: "生成脚本" }).click();
  await expect(page.getByText("SUPPORTED FACTS · 1")).toBeVisible();
  await page.getByRole("button", { name: "创建生成任务" }).click();
  await expect(page.getByRole("status")).toHaveText("任务完成", { timeout: 20_000 });
  await page.getByRole("link", { name: "查看脚本" }).click();

  await expect(page.getByRole("heading", { name: "结构化脚本" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "校验通过" })).toBeVisible();
  await page.getByRole("button", { name: "创建版本二" }).click();
  await expect(page.getByLabel("脚本版本")).toHaveValue(/.+/);
  await page.getByRole("link", { name: "比较版本" }).click();
  await expect(page.getByRole("heading", { name: "版本差异" })).toBeVisible();
  await expect(page.getByText("titles[0]")).toBeVisible();
  await page.goBack();

  const jsonDownload = page.waitForEvent("download");
  await page.getByRole("link", { name: "导出 JSON" }).click();
  expect((await jsonDownload).suggestedFilename()).toMatch(/script-.+\.json/);
  const markdownDownload = page.waitForEvent("download");
  await page.getByRole("link", { name: "导出 Markdown" }).click();
  expect((await markdownDownload).suggestedFilename()).toMatch(/script-.+\.md/);
});
