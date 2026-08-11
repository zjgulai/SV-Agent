import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { TestApp } from "../../test/TestApp";

describe("generation jobs", () => {
  it("restores a queued job and stops polling at validation_failed", async () => {
    render(<TestApp initialEntries={["/jobs/job-1"]} />);

    expect(await screen.findByText("正在生成")).toBeVisible();
    expect(await screen.findByText("脚本包含无证据声明", {}, { timeout: 2000 })).toBeVisible();
    expect(screen.getByRole("status")).toHaveTextContent("校验未通过");
    expect(screen.getByRole("link", { name: "查看脚本" })).toHaveAttribute(
      "href",
      "/scripts/script-1",
    );
  });
});
