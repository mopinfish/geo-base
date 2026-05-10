import { test, expect } from "../fixtures/authenticated-test";

import { resetDatabase } from "../utils/reset-db";
import { createApiKey } from "../fixtures/factories";
import { loginAsAdmin } from "../utils/session";

test.beforeAll(async () => {
  await loginAsAdmin();
  await resetDatabase();
  await createApiKey({ name: "smoke-key-1" });
  await createApiKey({ name: "smoke-key-2" });
});

test("AK-01 @smoke API キー一覧が表示される（key 値はマスクされている）", async ({
  page,
}) => {
  await page.goto("/api-keys");

  const rows = page.getByTestId("api-key-row");
  await expect(rows).toHaveCount(2);

  const masks = page.getByTestId("api-key-masked");
  await expect(masks.first()).toBeVisible();
  // マスク済みは `*` または `•` を含むはず
  await expect(masks.first()).toContainText(/[*•]/);
});
