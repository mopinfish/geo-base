import { test } from "../fixtures/authenticated-test";
import { expectNoA11ySeriousViolations } from "./_helper";

test("a11y: / serious/critical 違反なし", async ({ page }) => {
  await page.goto("/");
  await expectNoA11ySeriousViolations(page);
});
