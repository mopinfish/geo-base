import { test } from "@playwright/test";
import { expectNoA11ySeriousViolations } from "../a11y/_helper";

test("a11y: /login serious/critical 違反なし", async ({ page }) => {
  await page.goto("/login");
  await expectNoA11ySeriousViolations(page);
});
