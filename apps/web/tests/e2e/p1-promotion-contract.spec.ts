import { expect, test } from "@playwright/test";

test("an active Promotion Fact is final-CTA-only and invalidates approval when rejected", async ({ page }) => {
  await page.goto("/products/new");
  await page.getByLabel("商品名称").fill("Promotion Contract E2E");
  await page.getByLabel("商品描述").fill("The pouch is resealable");
  await page.getByRole("button", { name: "保存商品" }).click();

  await page.getByRole("button", { name: "确认" }).click();
  await page.getByRole("button", { name: "锁定" }).click();
  const productUrl = page.url();

  const start = "2000-01-01T00:00:00-08:00";
  const end = "2100-01-01T00:00:00-08:00";
  await page.getByLabel("优惠类型").selectOption("percent_off");
  await page.getByRole("textbox", { name: "百分比", exact: true }).fill("10");
  await page.getByLabel("开始（含 UTC offset）").fill(start);
  await page.getByLabel("结束（含 UTC offset）").fill(end);
  await page.getByLabel("人工证据摘录").fill("E2E operator promotion window");
  await page.getByRole("button", { name: "添加 Promotion Fact" }).click();

  const promotionRow = page.locator(".fact-row").filter({ hasText: "10% off on TikTok Shop in the US." });
  await expect(promotionRow).toBeVisible();
  await promotionRow.getByRole("button", { name: "确认" }).click();
  await expect(promotionRow.getByText("已确认")).toBeVisible();

  await page.getByRole("link", { name: "生成脚本" }).click();
  await page.getByLabel("创意结构").selectOption("offer_cta");
  await page.getByLabel("受众创意槽").selectOption("work_routine");
  await page.getByRole("combobox", { name: /Promotion Fact/ }).selectOption({ label: "10% off on TikTok Shop in the US." });
  await page.getByRole("button", { name: "纳入" }).click();
  await page.getByRole("button", { name: "创建生成任务" }).click();
  await expect(page.getByRole("status")).toHaveText("任务完成", { timeout: 20_000 });
  await page.getByRole("link", { name: "查看脚本" }).click();

  await expect(page.getByRole("heading", { name: "校验通过" })).toBeVisible();
  const promotion = page.getByText("10% off on TikTok Shop in the US.");
  await expect(promotion).toBeVisible();
  await expect(promotion.locator("xpath=ancestor::article[contains(@class, 'shot')]")).toContainText("cta");

  await page.getByRole("link", { name: "分镜预检" }).click();
  await page.getByRole("button", { name: "创建审核版分镜" }).click();
  await page.getByRole("button", { name: "批准" }).click();
  await expect(page.getByText("已批准用于未来报价门禁")).toBeVisible();
  const storyboardUrl = page.url();

  await page.goto(productUrl);
  await promotionRow.getByRole("button", { name: "否决" }).click();
  await expect(promotionRow.getByText("已否决")).toBeVisible();
  await page.goto(storyboardUrl);
  await expect(page.getByText("批准已失效")).toBeVisible();
});
