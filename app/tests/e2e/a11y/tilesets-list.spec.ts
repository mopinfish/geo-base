import { test } from "../fixtures/authenticated-test";

import { resetDatabase } from "../utils/reset-db";
import { createTileset } from "../fixtures/factories";
import { loginAsAdmin } from "../utils/session";
import { expectNoA11ySeriousViolations } from "./_helper";

test.describe("a11y: /tilesets", () => {
  test.beforeAll(async () => {
    await loginAsAdmin();
    await resetDatabase();
    await createTileset({
      name: "a11y-fixture",
      type: "vector",
      isPublic: true,
    });
  });

  test("a11y: /tilesets serious/critical 違反なし", async ({ page }) => {
    await page.goto("/tilesets");
    await expectNoA11ySeriousViolations(page);
  });
});
